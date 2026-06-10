"""Study orchestration: Optuna drives trials; Claude steers every N trials.

A :class:`StudySession` owns the Optuna study, the (mutable) :class:`SearchSpace`, and the
:class:`ClaudeAdvisor`. It runs ``study.optimize`` with a per-trial callback that, every
``advisor_every_n`` completed trials, consults Claude and applies the returned decision —
adjusting reward weights, re-centering the search space, or stopping the study.

Sessions are tracked in a module-level registry so the API can read progress and request a
stop. Designed to run in a background thread; all user-visible output goes through a logging
callback (so it works with the thread-safe TaskManager).
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from . import advisor as advisor_mod
from . import config_io, monitor_client, paths, trial_runner
from .search_space import SearchSpace

LogFn = Callable[[str, str], None]


@dataclass
class StudyConfig:
    project: str
    n_trials: int = 20
    advisor_every_n: int = 5
    trial_timesteps: int = 30_000
    gazebo_headless: bool = True
    max_stages: Optional[int] = None  # curriculum: train only the first N stages (None = all, scaled)
    monitor_base_url: Optional[str] = None  # Train Monitor API base (default :8006)
    mock_objective: bool = False
    include_hyperparams: bool = True
    include_reward_weights: bool = True
    include_reward_params: bool = True
    study_name: Optional[str] = None
    trial_timeout: Optional[float] = None


def apply_decision(space: SearchSpace, decision: dict[str, Any], log: LogFn) -> dict[str, Any]:
    """Mutate the search space per a Claude decision; return a structured diff for the record."""
    diffs: list[dict] = []
    for ov in decision.get("reward_weight_overrides") or []:
        d = space.recenter(f"rw.{ov['id']}", float(ov["value"]))
        if d:
            diffs.append(d)
    for ov in decision.get("reward_param_overrides") or []:
        d = space.recenter(f"rp.{ov['id']}.{ov['param']}", float(ov["value"]), band=0.4)
        if d:
            diffs.append(d)
    for ov in decision.get("search_space_overrides") or []:
        d = space.edit(ov["name"], low=ov.get("low"), high=ov.get("high"),
                       log=ov.get("log"), fix=ov.get("fix"))
        if d:
            diffs.append(d)
    applied = {"action": decision.get("action"), "rationale": decision.get("rationale"),
               "stop": bool(decision.get("stop")), "changes": diffs}
    for d in diffs:
        log("advisor", f"  re-bound {d['name']}: {d['before'].get('low')}..{d['before'].get('high')}"
                       f" -> {d['after'].get('low')}..{d['after'].get('high')}"
                       + (f" fix={d['after'].get('fixed')}" if d['after'].get('fixed') is not None else ""))
    return applied


@dataclass
class StudySession:
    config: StudyConfig
    log: LogFn = lambda level, msg: None
    status: str = "pending"
    error: Optional[str] = None
    space: Optional[SearchSpace] = None
    best: Optional[dict] = None
    decisions: list[dict] = field(default_factory=list)
    stop_requested: bool = False
    _study: Any = None
    _tuning_dir: Optional[Path] = None

    def request_stop(self) -> None:
        self.stop_requested = True
        if self._study is not None:
            self._study.stop()

    # ---- snapshot for the API ----
    def to_status(self) -> dict[str, Any]:
        n_done = len(self._study.trials) if self._study is not None else 0
        return {
            "status": self.status,
            "error": self.error,
            "project": self.config.project,
            "study_name": self.config.study_name,
            "n_trials": self.config.n_trials,
            "n_completed": n_done,
            "advisor_every_n": self.config.advisor_every_n,
            "mock_objective": self.config.mock_objective,
            "best": self.best,
            "decisions": self.decisions,
            "search_space": self.space.snapshot() if self.space else [],
        }

    # ---- main entry (run in a thread) ----
    def run(self) -> None:
        try:
            self._run()
            self.status = "stopped" if self.stop_requested else "complete"
            self.log("info", f"Study finished ({self.status}). Best: {self.best}")
        except Exception as exc:  # surface, don't crash the thread silently
            self.error = str(exc)
            self.status = "error"
            self.log("error", f"Study failed: {exc}")
            self.log("error", traceback.format_exc())

    def _run(self) -> None:
        import optuna

        cfg = self.config
        if cfg.study_name is None:
            cfg.study_name = "study_" + time.strftime("%Y%m%d_%H%M%S")
        rl_config, ppo_config = config_io.load_base(cfg.project)
        terms = config_io.reward_terms(rl_config)
        self.space = SearchSpace.from_base(
            terms,
            include_hyperparams=cfg.include_hyperparams,
            include_reward_weights=cfg.include_reward_weights,
            include_reward_params=cfg.include_reward_params,
        )
        self._tuning_dir = paths.tuning_root(cfg.project) / cfg.study_name
        self._tuning_dir.mkdir(parents=True, exist_ok=True)
        decisions_path = self._tuning_dir / "decisions.jsonl"

        # Training runs through the Train Monitor — the single training controller.
        monitor = monitor_client.TrainMonitorClient(cfg.monitor_base_url, log=self.log)

        advisor = advisor_mod.make_advisor(log=self.log)
        self.log("info", f"Advisor: {advisor.describe()}")
        self.log("info", f"Search space: {len(self.space.names())} params, "
                         f"{cfg.n_trials} trials, advise every {cfg.advisor_every_n}.")
        if cfg.mock_objective:
            self.log("warn", "MOCK objective: NOT training — synthetic scores (loop test only).")
        else:
            if not monitor.reachable():
                raise RuntimeError(
                    f"Train Monitor not reachable at {monitor.base}. Start its backend "
                    f"(port 8006) or set QUADRL_TRAIN_MONITOR_URL — the predictor drives "
                    f"training through the Train Monitor's start/stop/resume.")
            self.log("info", f"REAL training: each trial runs via the Train Monitor "
                             f"({monitor.base}) — headless={cfg.gazebo_headless}, "
                             f"{cfg.trial_timesteps} timestep budget.")
            cur = (rl_config.get("curriculum") or {})
            if cur.get("enabled") and cur.get("stages"):
                preview = config_io.materialize(rl_config, ppo_config, {},
                                               total_timesteps=cfg.trial_timesteps,
                                               max_stages=cfg.max_stages)
                stages = (preview.get("curriculum") or {}).get("stages") or []
                breakdown = ", ".join(f"{s.get('id')}={s.get('timesteps')}" for s in stages)
                self.log("info", f"Curriculum: {len(stages)} stage(s) scaled to budget -> {breakdown}")

        storage = f"sqlite:///{self._tuning_dir / 'optuna.db'}"
        self._study = optuna.create_study(
            study_name=cfg.study_name, storage=storage, direction="maximize",
            sampler=optuna.samplers.TPESampler(), load_if_exists=True,
        )

        def objective(trial: "optuna.trial.Trial") -> float:
            sampled = self.space.sample(trial)
            if cfg.mock_objective:
                value = trial_runner.mock_objective(sampled)
                self.log("trial", f"trial {trial.number}: mock objective = {value}")
                return value
            trial_cfg = config_io.materialize(rl_config, ppo_config, sampled,
                                              total_timesteps=cfg.trial_timesteps,
                                              max_stages=cfg.max_stages)
            cfg_path = config_io.write_trial_config(
                trial_cfg, self._tuning_dir / f"trial_{trial.number}" / "config.yaml")
            self.log("trial", f"trial {trial.number}: starting training via Train Monitor "
                             f"({cfg.trial_timesteps} step budget) -> {cfg_path}")
            t0 = time.time()
            status = monitor.run_to_completion(
                cfg.project, cfg_path, gazebo_headless=cfg.gazebo_headless,
                timeout=cfg.trial_timeout, should_stop=lambda: self.stop_requested)
            run_root = trial_runner.resolve_run_dir(cfg.project, status.get("run_id"), after=t0)
            value, series = trial_runner.read_objective(run_root)
            self.log("trial", f"trial {trial.number}: objective = {value} "
                             f"(from {len(series)} eval points, run={run_root.name})")
            return value

        def callback(study: "optuna.study.Study", trial: "optuna.trial.FrozenTrial") -> None:
            # Track best.
            try:
                self.best = {"number": study.best_trial.number,
                             "value": round(float(study.best_value), 5),
                             "params": {k: round(v, 6) if isinstance(v, float) else v
                                        for k, v in study.best_params.items()}}
            except Exception:
                pass  # no completed trial yet → no best
            if self.stop_requested:
                study.stop()
                return
            n_done = len([t for t in study.trials
                          if t.state == optuna.trial.TrialState.COMPLETE])
            if n_done == 0 or n_done % cfg.advisor_every_n != 0:
                return
            if n_done >= cfg.n_trials:
                return  # no point advising after the last trial
            self.log("advisor", f"--- Consulting Claude after {n_done} trials ---")
            decision = advisor.advise(study, self.space)
            if decision is None:
                return
            self.log("advisor", f"action={decision.get('action')} :: {decision.get('rationale')}")
            applied = apply_decision(self.space, decision, self.log)
            applied["after_trial"] = n_done
            applied["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            self.decisions.append(applied)
            with open(decisions_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(applied) + "\n")
            if applied["stop"] or decision.get("action") == "stop":
                self.log("advisor", "Claude requested STOP.")
                study.stop()

        self.status = "running"
        self._study.optimize(objective, n_trials=cfg.n_trials, callbacks=[callback])


# ---- session registry (shared with the API layer) ----
SESSIONS: dict[str, StudySession] = {}


def register(task_id: str, session: StudySession) -> None:
    SESSIONS[task_id] = session


def get(task_id: str) -> Optional[StudySession]:
    return SESSIONS.get(task_id)
