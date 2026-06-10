"""Sequential per-stage tuning — a greedy, stage-by-stage curriculum tuner.

Unlike :class:`tuner.study.StudySession` (one global study, one shared param set), this runs an
**Optuna sub-study per curriculum stage**: tune stage k's own reward terms against stage k's
objective, lock the best, freeze its checkpoint, then tune stage k+1 warm-started from it.

Each trial trains ONLY stage k via the Train Monitor — a per-trial config truncated to stages
``0..k`` (:func:`tuner.config_io.materialize_stage`) plus ``--start-stage k`` + ``--resume <seed>``
(see :mod:`tuner.monitor_client`). The winning trial's checkpoint becomes the seed for k+1
(:mod:`tuner.checkpoints`). Progress persists to ``sequence.json`` so a stopped run resumes from
the first un-tuned stage. Set ``mock_objective`` to exercise the whole loop with synthetic scores
(no training, no monitor, no checkpoints).

Design: training-predictor/docs/PHASE1_SEQUENTIAL_TUNING.md
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from . import advisor as advisor_mod
from . import checkpoints, config_io, monitor_client, paths, trial_runner
from . import study as study_mod
from .search_space import SearchSpace

LogFn = Callable[[str, str], None]


@dataclass
class StageSeqConfig:
    project: str
    stages_to_tune: list[int]                 # 0-based stage indices (by order), e.g. [0,1,2]
    trials_per_stage: int = 10
    timesteps_per_stage: int = 30_000
    advisor_every_n: int = 5
    gazebo_headless: bool = True
    trial_timeout: Optional[float] = None
    mock_objective: bool = False
    monitor_base_url: Optional[str] = None
    seq_name: Optional[str] = None


def _mock_stage_objective(sampled: dict[str, Any], stage_index: int) -> float:
    """Deterministic synthetic score (no training) for loop testing — has a clear, stage-shifted
    optimum so Optuna visibly improves and the advisor has a signal to reason about."""
    score = 1.0
    for i, name in enumerate(sorted(sampled)):
        v = sampled[name]
        if isinstance(v, (int, float)):
            target = 0.4 + 0.08 * stage_index + 0.03 * (i % 5)
            score -= (float(v) - target) ** 2
    return round(score, 6)


@dataclass
class StageSequenceSession:
    config: StageSeqConfig
    log: LogFn = lambda level, msg: None
    mode: str = "sequential_stage"
    status: str = "pending"
    error: Optional[str] = None
    stop_requested: bool = False
    current_stage_index: Optional[int] = None
    stage_results: dict[int, dict] = field(default_factory=dict)   # stage_index -> result dict
    # mirrors of the *current* stage, so the existing status/trials UI keeps working:
    decisions: list[dict] = field(default_factory=list)
    best: Optional[dict] = None
    space: Optional[SearchSpace] = None
    _study: Any = None
    _stages: list[dict] = field(default_factory=list)
    _seq_dir: Optional[Path] = None
    _seed: Optional[str] = None

    # ---- control ----
    def request_stop(self) -> None:
        self.stop_requested = True
        if self._study is not None:
            self._study.stop()

    # ---- snapshot for the API ----
    def to_status(self) -> dict[str, Any]:
        n_completed = len(self._study.trials) if self._study is not None else 0
        return {
            "mode": self.mode,
            "status": self.status,
            "error": self.error,
            "project": self.config.project,
            "seq_name": self.config.seq_name,
            "study_name": self.config.seq_name,        # alias for the shared UI
            "mock_objective": self.config.mock_objective,
            "current_stage_index": self.current_stage_index,
            "total_stages": len(self._stages),
            "stages_to_tune": self.config.stages_to_tune,
            "trials_per_stage": self.config.trials_per_stage,
            "stages": [self.stage_results[k] for k in sorted(self.stage_results)],
            # current-stage mirrors (so Best so far / Trials / Insights render):
            "best": self.best,
            "decisions": self.decisions,
            "search_space": self.space.snapshot() if self.space else [],
            "n_trials": self.config.trials_per_stage,
            "n_completed": n_completed,
        }

    # ---- main entry (run in a thread) ----
    def run(self) -> None:
        try:
            self._run()
            self.status = "stopped" if self.stop_requested else "complete"
            self.log("info", f"Sequence finished ({self.status}).")
        except Exception as exc:
            self.error = str(exc)
            self.status = "error"
            self.log("error", f"Sequence failed: {exc}")
            self.log("error", traceback.format_exc())

    def _run(self) -> None:
        import optuna

        cfg = self.config
        if cfg.seq_name is None:
            cfg.seq_name = "seq_" + time.strftime("%Y%m%d_%H%M%S")
        rl, ppo = config_io.load_base(cfg.project)
        cur = rl.get("curriculum") or {}
        self._stages = sorted((cur.get("stages") or []), key=lambda s: s.get("order", 0))
        if not (cur.get("enabled") and self._stages):
            raise RuntimeError("Sequential per-stage tuning requires a curriculum with stages.")
        for k in cfg.stages_to_tune:
            if not (0 <= k < len(self._stages)):
                raise RuntimeError(f"stage index {k} out of range (0..{len(self._stages) - 1})")

        self._seq_dir = paths.tuning_root(cfg.project) / cfg.seq_name
        self._seq_dir.mkdir(parents=True, exist_ok=True)
        self._load_sequence()                       # resume: restore prior results + seed

        monitor = None
        if not cfg.mock_objective:
            monitor = monitor_client.TrainMonitorClient(cfg.monitor_base_url, log=self.log)
            if not monitor.reachable():
                raise RuntimeError(
                    f"Train Monitor not reachable at {monitor.base}. Start its backend (port 8006) "
                    f"or set QUADRL_TRAIN_MONITOR_URL — real trials train through the Train Monitor.")
            self.log("info", f"REAL per-stage training via the Train Monitor ({monitor.base}).")
        else:
            self.log("warn", "MOCK objective: NOT training — synthetic per-stage scores (loop test).")

        # seed result rows
        for k in cfg.stages_to_tune:
            if k not in self.stage_results:
                st = self._stages[k]
                self.stage_results[k] = {
                    "stage_index": k, "stage_id": st.get("id"),
                    "stage_name": st.get("name") or st.get("id"),
                    "status": "pending", "n_completed": 0,
                    "best_value": None, "best_params": {},
                    "seed_checkpoint": None, "decisions": [],
                }

        self.status = "running"
        for k in cfg.stages_to_tune:
            if self.stop_requested:
                break
            result = self.stage_results[k]
            if result.get("status") == "done":
                self._seed = result.get("seed_checkpoint") or self._seed
                self.log("info", f"Stage {k} ({result['stage_name']}) already tuned — skipping.")
                continue
            self._tune_stage(k, rl, ppo, monitor, optuna)
            self._save_sequence()

    def _tune_stage(self, k: int, rl: dict, ppo: dict, monitor, optuna) -> None:
        cfg = self.config
        stage = self._stages[k]
        self.current_stage_index = k
        result = self.stage_results[k]
        result["status"] = "running"
        self.decisions = result["decisions"]        # surface this stage's decisions
        self.best = None

        space = SearchSpace.from_base(
            stage.get("reward_terms") or [],
            include_hyperparams=False, include_reward_weights=True, include_reward_params=True)
        self.space = space
        n_params = len(space.names())
        target_trials = cfg.trials_per_stage if n_params else 1   # nothing to tune ⇒ one run for the seed

        stage_dir = self._seq_dir / f"stage_{k}"
        stage_dir.mkdir(parents=True, exist_ok=True)
        decisions_path = stage_dir / "decisions.jsonl"

        study = optuna.create_study(
            study_name=f"{cfg.seq_name}_stage_{k}", storage=f"sqlite:///{stage_dir / 'optuna.db'}",
            direction="maximize", sampler=optuna.samplers.TPESampler(), load_if_exists=True)
        self._study = study
        advisor = advisor_mod.make_advisor(log=self.log)
        self.log("info", f"=== Stage {k} ({stage.get('name')}) — {n_params} reward param(s), "
                         f"target {target_trials} trial(s) ===")

        def objective(trial: "optuna.trial.Trial") -> float:
            sampled = space.sample(trial)
            if cfg.mock_objective:
                value = _mock_stage_objective(sampled, k)
                self.log("trial", f"stage {k} trial {trial.number}: mock objective = {value}")
                return value
            cfg_dict = config_io.materialize_stage(
                rl, ppo, sampled, stage_index=k, budget=cfg.timesteps_per_stage)
            cfg_path = config_io.write_trial_config(
                cfg_dict, stage_dir / f"trial_{trial.number}" / "config.yaml")
            self.log("trial", f"stage {k} trial {trial.number}: training stage '{stage.get('id')}' "
                             f"({'from scratch' if (k == 0 or self._seed is None) else 'resumed'})")
            t0 = time.time()
            if k == 0 or self._seed is None:
                status = monitor.run_to_completion(
                    cfg.project, cfg_path, gazebo_headless=cfg.gazebo_headless,
                    timeout=cfg.trial_timeout, should_stop=lambda: self.stop_requested)
            else:
                status = monitor.run_to_completion(
                    cfg.project, cfg_path, resume_checkpoint=self._seed, resume_start_stage=k,
                    gazebo_headless=cfg.gazebo_headless, timeout=cfg.trial_timeout,
                    should_stop=lambda: self.stop_requested)
            run_root = trial_runner.resolve_run_dir(cfg.project, status.get("run_id"), after=t0)
            value, series = trial_runner.read_objective(run_root)
            captured = checkpoints.capture_stage_ckpt(
                cfg.project, stage, cfg_dict, dest=stage_dir / f"trial_{trial.number}_ckpt.zip")
            if captured is not None:
                trial.set_user_attr("ckpt", str(captured))
            self.log("trial", f"stage {k} trial {trial.number}: objective = {value} "
                             f"({len(series)} eval pts, run={run_root.name})")
            return value

        def callback(study: "optuna.study.Study", trial: "optuna.trial.FrozenTrial") -> None:
            try:
                result["best_value"] = round(float(study.best_value), 5)
                result["best_params"] = {kk: (round(v, 6) if isinstance(v, float) else v)
                                         for kk, v in study.best_params.items()}
                self.best = {"number": study.best_trial.number, "value": result["best_value"],
                             "params": result["best_params"]}
            except Exception:
                pass
            result["n_completed"] = len(
                [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
            if self.stop_requested:
                study.stop()
                return
            n_done = result["n_completed"]
            if n_params == 0 or n_done == 0 or n_done % cfg.advisor_every_n != 0 or n_done >= target_trials:
                return
            self.log("advisor", f"--- Consulting Claude (stage {k}) after {n_done} trials ---")
            decision = advisor.advise(study, space)
            if decision is None:
                return
            applied = study_mod.apply_decision(space, decision, self.log)
            applied.update(after_trial=n_done, stage_index=k,
                           timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"))
            result["decisions"].append(applied)
            with open(decisions_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(applied) + "\n")
            if applied["stop"] or decision.get("action") == "stop":
                self.log("advisor", "Claude requested STOP for this stage.")
                study.stop()

        n_existing = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
        remaining = max(0, target_trials - n_existing)
        if remaining:
            study.optimize(objective, n_trials=remaining, callbacks=[callback])

        if self.stop_requested:
            result["status"] = "stopped"
            return

        # promote the winning trial's checkpoint as the frozen seed for the next stage
        if not cfg.mock_objective:
            try:
                best_trial = study.best_trial
            except ValueError as exc:
                raise RuntimeError(f"Stage {k}: no successful trials to seed the next stage.") from exc
            cap = best_trial.user_attrs.get("ckpt")
            if not (cap and Path(cap).is_file()):
                raise RuntimeError(f"Stage {k}: best trial produced no usable checkpoint.")
            seed = checkpoints.promote_best(Path(cap), stage_dir / "best_ckpt.zip")
            self._seed = str(seed)
            result["seed_checkpoint"] = str(seed)
            checkpoints.cleanup_trial_ckpts(stage_dir)        # best is now best_ckpt.zip

        result["status"] = "done"
        self.log("info", f"Stage {k} ({stage.get('name')}) done — best {result['best_value']}")

    # ---- final apply (called by the API on user confirm) ----
    def best_stage_params(self) -> dict[int, dict[str, Any]]:
        """{stage_index: winning rw.*/rp.* params} for stages that completed with a best."""
        return {k: r["best_params"] for k, r in self.stage_results.items()
                if r.get("status") == "done" and r.get("best_params")}

    # ---- persistence ----
    def _save_sequence(self) -> None:
        if self._seq_dir is None:
            return
        data = {
            "seq_name": self.config.seq_name, "project": self.config.project,
            "stages_to_tune": self.config.stages_to_tune, "last_seed": self._seed,
            "stage_results": {str(k): v for k, v in self.stage_results.items()},
        }
        (self._seq_dir / "sequence.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_sequence(self) -> None:
        p = self._seq_dir / "sequence.json"
        if not p.is_file():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return
        self._seed = data.get("last_seed")
        for ks, v in (data.get("stage_results") or {}).items():
            self.stage_results[int(ks)] = v
        n_done = sum(1 for r in self.stage_results.values() if r.get("status") == "done")
        if n_done:
            self.log("info", f"Resuming sequence '{self.config.seq_name}' — {n_done} stage(s) already done.")
