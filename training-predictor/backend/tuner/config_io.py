"""Load base configs and materialize a self-contained per-trial training config.

The RL Trainer export (``rl_<project>_config.yaml``) keeps PPO hyperparameters in a
separate ``ppo_<project>_config.yaml`` referenced via ``ppo_config_file``. The launcher's
``_merge_ppo_config`` *overwrites* the top-level ``hyperparameters`` from that file when the
pointer is present — so to make a trial's sampled hyperparameters stick we inline them and
**drop ``ppo_config_file``**. ``total_timesteps`` lives inside ``hyperparameters`` (the
launcher reads it there), so the per-trial proxy budget is set there too.

Sampled parameter names are namespaced:
  ``hp.<name>``            PPO hyperparameter (learning_rate, n_steps, …)
  ``rw.<term_id>``         reward-term weight *magnitude* (sign taken from the base term)
  ``rp.<term_id>.<param>`` reward-term param (e.g. ``rp.upright.sigma``)
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from . import paths

# PPO blocks that normally arrive via ppo_config_file; inlined so the trial config is standalone.
_PPO_PASSTHROUGH = ("parallel", "device", "checkpoint", "best_model")


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_base(project: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (rl_config, ppo_config) for a project. Raises FileNotFoundError if missing."""
    rl_path = paths.base_rl_config(project)
    if not rl_path.is_file():
        raise FileNotFoundError(f"No RL config for project '{project}': {rl_path}")
    rl = load_yaml(rl_path)
    ppo_path = paths.base_ppo_config(project)
    ppo = load_yaml(ppo_path) if ppo_path.is_file() else {}
    return rl, ppo


def _apply_timestep_budget(
    cfg: dict[str, Any], hp: dict[str, Any], budget: int, max_stages: Optional[int]
) -> None:
    """Make the trial honour ``budget`` whether or not the project uses a curriculum.

    Curriculum on: truncate to the first ``max_stages`` stages (if given) and scale each
    stage's ``timesteps`` so they sum to ~budget, keeping the relative stage lengths, with a
    one-rollout floor per stage. Curriculum off: just set ``hyperparameters.total_timesteps``.
    """
    cur = cfg.get("curriculum") or {}
    stages = cur.get("stages") or []
    if not (cur.get("enabled") and stages):
        hp["total_timesteps"] = int(budget)
        return

    stages = sorted(stages, key=lambda s: s.get("order", 0))
    if max_stages:
        stages = stages[: int(max_stages)]
    weights = [max(1, int(s.get("timesteps", 0))) for s in stages]
    total_w = sum(weights) or 1
    num_envs = max(1, int((cfg.get("parallel") or {}).get("num_envs", 1)))
    floor = int(hp.get("n_steps", 2048)) * num_envs  # at least one rollout per stage
    for s, w in zip(stages, weights):
        s["timesteps"] = max(floor, round(budget * w / total_w))
    cur["stages"] = stages
    cur["current_stage_index"] = 0
    cur["total_timesteps"] = sum(int(s["timesteps"]) for s in stages)
    cfg["curriculum"] = cur


def reward_terms(rl_config: dict[str, Any]) -> list[dict[str, Any]]:
    return (rl_config.get("task") or {}).get("reward_terms") or []


def base_hyperparameters(rl_config: dict[str, Any], ppo_config: dict[str, Any]) -> dict[str, Any]:
    """Effective hyperparameters the launcher would use (PPO file wins, as it does at runtime)."""
    hp = dict(rl_config.get("hyperparameters") or {})
    hp.update(ppo_config.get("hyperparameters") or {})
    return hp


def materialize(
    rl_config: dict[str, Any],
    ppo_config: dict[str, Any],
    sampled: dict[str, Any],
    *,
    total_timesteps: int,
    max_stages: Optional[int] = None,
) -> dict[str, Any]:
    """Produce a standalone trial config dict from the base configs + a trial's sampled params.

    ``total_timesteps`` is the per-trial proxy budget. For curriculum projects it is spread
    across the (optionally truncated) stages in proportion to their original lengths, since the
    launcher trains per-stage and ignores the top-level ``total_timesteps`` there.
    """
    cfg = copy.deepcopy(rl_config)
    cfg.pop("ppo_config_file", None)  # otherwise _merge_ppo_config clobbers our hyperparameters

    # ---- hyperparameters (base PPO + sampled overrides + proxy budget) ----
    hp = base_hyperparameters(rl_config, ppo_config)
    for key, value in sampled.items():
        if key.startswith("hp."):
            hp[key[3:]] = value
    hp["total_timesteps"] = int(total_timesteps)
    cfg["hyperparameters"] = hp

    # Inline the remaining PPO blocks so the trial config is self-contained.
    for key in _PPO_PASSTHROUGH:
        if key in ppo_config and key not in cfg:
            cfg[key] = copy.deepcopy(ppo_config[key])

    _apply_timestep_budget(cfg, hp, int(total_timesteps), max_stages)

    # ---- reward weights & params ----
    apply_reward_samples(reward_terms(cfg), sampled)

    return cfg


def apply_reward_samples(terms: list[dict[str, Any]], sampled: dict[str, Any]) -> None:
    """Write sampled reward overrides into ``terms`` in place.

    ``rw.<id>`` sets the term's weight *magnitude* (the base term's sign — reward vs penalty —
    is preserved); ``rp.<id>.<param>`` sets a shaping param. Keys for unknown term ids and
    non-reward keys (e.g. ``hp.*``) are ignored. Shared by :func:`materialize` (global
    ``task.reward_terms``) and :func:`materialize_stage` (a single stage's ``reward_terms``).
    """
    by_id = {t.get("id"): t for t in terms}
    for key, value in sampled.items():
        if key.startswith("rw."):
            term = by_id.get(key[3:])
            if term is not None:
                sign = -1.0 if (term.get("type") == "penalty" or float(term.get("weight", 0.0)) < 0) else 1.0
                term["weight"] = sign * abs(float(value))
        elif key.startswith("rp."):
            parts = key.split(".", 2)
            if len(parts) == 3:
                term = by_id.get(parts[1])
                if term is not None:
                    term.setdefault("params", {})[parts[2]] = value


def materialize_stage(
    rl_config: dict[str, Any],
    ppo_config: dict[str, Any],
    sampled: dict[str, Any],
    *,
    stage_index: int,
    budget: int,
) -> dict[str, Any]:
    """Per-trial config for SEQUENTIAL per-stage tuning — train ONLY stage ``stage_index``.

    Truncates the curriculum to stages ``0..stage_index`` so that ``--start-stage stage_index``
    (which skips the earlier stages and trains to the end of the config) trains just the target
    stage. The sampled ``rw.*/rp.*`` are written into THAT stage's own ``reward_terms`` — the
    block the trainer reads per stage (``stage_config()``), unlike the global :func:`materialize`.

    PPO hyperparameters are kept from the base config (curriculum-wide, not tuned per stage in
    Phase 1); any ``hp.*`` samples are still applied for forward-compatibility. Raises
    ``ValueError`` if the project has no curriculum stages or ``stage_index`` is out of range.
    """
    cfg = copy.deepcopy(rl_config)
    cfg.pop("ppo_config_file", None)  # otherwise _merge_ppo_config clobbers our hyperparameters

    hp = base_hyperparameters(rl_config, ppo_config)
    for key, value in sampled.items():
        if key.startswith("hp."):
            hp[key[3:]] = value
    hp["total_timesteps"] = int(budget)
    cfg["hyperparameters"] = hp
    for key in _PPO_PASSTHROUGH:
        if key in ppo_config and key not in cfg:
            cfg[key] = copy.deepcopy(ppo_config[key])

    cur = cfg.get("curriculum") or {}
    stages = sorted((cur.get("stages") or []), key=lambda s: s.get("order", 0))
    if not stages:
        raise ValueError("materialize_stage requires a curriculum with stages")
    if not (0 <= stage_index < len(stages)):
        raise ValueError(f"stage_index {stage_index} out of range (0..{len(stages) - 1})")

    truncated = stages[: stage_index + 1]
    target = truncated[stage_index]
    target["timesteps"] = int(budget)
    apply_reward_samples(target.get("reward_terms") or [], sampled)

    cur["enabled"] = True
    cur["stages"] = truncated
    cfg["curriculum"] = cur
    return cfg


def write_trial_config(cfg: dict[str, Any], dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    return dest
