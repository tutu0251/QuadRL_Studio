"""Write confirmed tuned parameters back into a project's export configs.

Once the user confirms the predicted parameters, this persists them to the SAME files the
editors/Train Monitor read:
  * PPO hyperparameters (``hp.*``) → ``exports/ppo_<project>_config.yaml`` ``hyperparameters``
    (falling back to the RL config's ``hyperparameters`` block if there is no PPO export).
  * Reward weights / params (``rw.* / rp.*``) → ``exports/rl_<project>_config.yaml``
    ``task.reward_terms`` (weight sign preserved from the base term).

Each edited file is backed up first (``<file>.bak-<timestamp>``).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from . import config_io, paths


def _backup(path: Path, stamp: str) -> str:
    bak = path.with_suffix(path.suffix + f".bak-{stamp}")
    bak.write_bytes(path.read_bytes())
    return str(bak)


def _dump(path: Path, doc: dict[str, Any], header: str) -> None:
    text = header + yaml.safe_dump(doc, default_flow_style=False, sort_keys=False)
    path.write_text(text, encoding="utf-8")


def apply_params(project: str, params: dict[str, Any], *, stamp: str | None = None) -> dict[str, Any]:
    """Persist ``params`` (``hp.* / rw.* / rp.*``) into the project's configs.

    Returns a summary of what was written (changed values, files, backups). Raises
    ``FileNotFoundError`` if the project's RL export is missing.
    """
    stamp = stamp or time.strftime("%Y%m%d_%H%M%S")
    rl, ppo = config_io.load_base(project)
    rl_path = paths.base_rl_config(project)
    ppo_path = paths.base_ppo_config(project)

    hp_changes = {k[3:]: v for k, v in params.items() if k.startswith("hp.")}
    weight_changes: dict[str, float] = {}
    param_changes: dict[str, dict[str, Any]] = {}

    summary: dict[str, Any] = {"project": project, "hyperparameters": {},
                               "reward_weights": {}, "reward_params": {},
                               "files": [], "backups": []}

    # ---- hyperparameters → PPO export (or RL config if no PPO export) ----
    if hp_changes:
        if ppo_path.is_file():
            ppo.setdefault("hyperparameters", {}).update(hp_changes)
            summary["backups"].append(_backup(ppo_path, stamp))
            _dump(ppo_path, ppo, "# PPO config — hyperparameters updated by Training Predictor\n")
            summary["files"].append(str(ppo_path))
        else:
            rl.setdefault("hyperparameters", {}).update(hp_changes)  # written below with RL file
        summary["hyperparameters"] = hp_changes

    # ---- reward weights / params → RL export task.reward_terms ----
    terms = config_io.reward_terms(rl)
    by_id = {t.get("id"): t for t in terms}
    for key, value in params.items():
        if key.startswith("rw."):
            tid = key[3:]
            term = by_id.get(tid)
            if term is not None:
                sign = -1.0 if (term.get("type") == "penalty" or float(term.get("weight", 0.0)) < 0) else 1.0
                term["weight"] = sign * abs(float(value))
                weight_changes[tid] = term["weight"]
        elif key.startswith("rp."):
            _, tid, pname = key.split(".", 2)
            term = by_id.get(tid)
            if term is not None:
                term.setdefault("params", {})[pname] = value
                param_changes.setdefault(tid, {})[pname] = value

    rl_touched = bool(weight_changes or param_changes) or (hp_changes and not ppo_path.is_file())
    if rl_touched:
        summary["backups"].append(_backup(rl_path, stamp))
        _dump(rl_path, rl, "# RL config — reward terms updated by Training Predictor\n")
        summary["files"].append(str(rl_path))

    summary["reward_weights"] = weight_changes
    summary["reward_params"] = param_changes
    return summary


def apply_stage_params(
    project: str,
    stage_params: dict[int, dict[str, Any]],
    *,
    stamp: str | None = None,
) -> dict[str, Any]:
    """Persist SEQUENTIAL per-stage tuning results into the project's RL config.

    ``stage_params`` maps a curriculum stage index (0-based, by ``order``) to that stage's
    winning ``rw.* / rp.*`` overrides. Each is written into ``curriculum.stages[idx].reward_terms``
    — the per-stage block the trainer reads (``stage_config()``) — with the term's sign preserved.
    The RL config is backed up once (``.bak-<timestamp>``). Hyperparameters are not touched
    (curriculum-wide, not tuned per stage in Phase 1). Raises ``FileNotFoundError`` if the RL
    export is missing.
    """
    stamp = stamp or time.strftime("%Y%m%d_%H%M%S")
    rl, _ = config_io.load_base(project)
    rl_path = paths.base_rl_config(project)

    cur = rl.get("curriculum") or {}
    stages = sorted((cur.get("stages") or []), key=lambda s: s.get("order", 0))

    summary: dict[str, Any] = {"project": project, "stages": {}, "files": [], "backups": []}
    changed = False
    for idx in sorted(stage_params):
        params = stage_params[idx] or {}
        if not (0 <= idx < len(stages)) or not params:
            continue
        stage = stages[idx]
        terms = stage.get("reward_terms") or []
        config_io.apply_reward_samples(terms, params)  # in place ⇒ mutates rl

        by_id = {t.get("id"): t for t in terms}
        weights: dict[str, float] = {}
        rparams: dict[str, dict[str, Any]] = {}
        for key, value in params.items():
            if key.startswith("rw.") and key[3:] in by_id:
                weights[key[3:]] = by_id[key[3:]].get("weight")
            elif key.startswith("rp."):
                bits = key.split(".", 2)
                if len(bits) == 3 and bits[1] in by_id:
                    rparams.setdefault(bits[1], {})[bits[2]] = value
        summary["stages"][idx] = {
            "id": stage.get("id"),
            "name": stage.get("name") or stage.get("id"),
            "reward_weights": weights,
            "reward_params": rparams,
        }
        changed = True

    if changed:
        summary["backups"].append(_backup(rl_path, stamp))
        _dump(rl_path, rl, "# RL config — per-stage reward terms updated by Training Predictor\n")
        summary["files"].append(str(rl_path))
    return summary
