"""Read a trial's objective from its training run, plus a mock objective for loop testing.

Training itself is launched through the RL Train Monitor (see :mod:`monitor_client`) — this
module no longer starts any training process; it only resolves the produced run directory and
reads the objective scalar from TensorBoard.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional

from . import paths

# Preferred objective scalar first.
_OBJECTIVE_TAGS = ("eval/mean_reward", "rollout/ep_rew_mean")


def resolve_run_dir(project: str, run_id: Optional[str], *, after: Optional[float] = None) -> Path:
    """Run-root directory for a finished trial: prefer the monitor-reported ``run_id``,
    else the newest dir under ``<project>/runs``."""
    runs_dir = paths.project_dir(project) / "runs"
    if run_id:
        candidate = runs_dir / run_id
        if candidate.is_dir():
            return candidate
    return _newest_run_dir(runs_dir, after=after)


def _newest_run_dir(runs_dir: Path, *, after: Optional[float] = None) -> Path:
    if not runs_dir.exists():
        raise RuntimeError(f"no runs directory at {runs_dir}")
    candidates = [p for p in runs_dir.iterdir()
                  if p.is_dir() and (after is None or p.stat().st_mtime >= after - 1)]
    if not candidates:
        raise RuntimeError(f"no run directory found under {runs_dir}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_objective(run_root: Path) -> tuple[float, list[float]]:
    """Return (final_value, full_series) for the best available objective scalar.

    ``final_value`` is the last recorded point (across curriculum stages, in stage order);
    ``full_series`` lets the caller report intermediate values if desired.
    """
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    event_files = sorted(run_root.rglob("events.out.tfevents.*"))
    if not event_files:
        raise RuntimeError(f"no TensorBoard event files under {run_root}")

    series_by_tag: dict[str, list[float]] = {tag: [] for tag in _OBJECTIVE_TAGS}
    for ev in event_files:
        acc = EventAccumulator(str(ev), size_guidance={"scalars": 0})
        acc.Reload()
        available = set(acc.Tags().get("scalars", []))
        for tag in _OBJECTIVE_TAGS:
            if tag in available:
                series_by_tag[tag].extend(s.value for s in acc.Scalars(tag))

    for tag in _OBJECTIVE_TAGS:
        series = [v for v in series_by_tag[tag] if not math.isnan(v)]
        if series:
            return float(series[-1]), series
    raise RuntimeError(
        f"none of {_OBJECTIVE_TAGS} found in TensorBoard logs under {run_root}")


def mock_objective(sampled: dict[str, Any]) -> float:
    """Cheap deterministic surrogate for testing the orchestration loop (no training run).

    A smooth, multi-modal function of a few sampled params with a clear optimum, so Optuna
    visibly improves and Claude has a signal to reason about.
    """
    lr = float(sampled.get("hp.learning_rate", 3e-4))
    ent = float(sampled.get("hp.ent_coef", 1e-3))
    clip = float(sampled.get("hp.clip_range", 0.2))
    upright = float(sampled.get("rw.upright", 0.8))

    score = 0.0
    score += math.exp(-((math.log10(lr) + 3.5) ** 2) / 0.5)   # optimum near lr=3e-4
    score += 0.5 * math.exp(-((math.log10(ent) + 2.5) ** 2) / 0.5)
    score -= 2.0 * (clip - 0.2) ** 2
    score -= 0.8 * (upright - 0.9) ** 2
    return round(score, 6)
