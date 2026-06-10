"""Locate and capture per-stage SB3 checkpoints for sequential per-stage tuning.

The trainer writes each curriculum stage's final checkpoint to the PROJECT-level checkpoint
directory as ``<basename>.zip`` (``basename`` from ``checkpoint.filename_template``, default
``ppo_{stage_id}``). Because that path is shared and overwritten by every trial of a stage —
and the Train Monitor runs trials serially — we copy a trial's checkpoint out as soon as the
trial finishes, then promote the winning copy as the frozen seed for the next stage.

The path/naming logic here mirrors ``training/scripts/run_rl_train.py``
(``_checkpoint_dir`` / ``_checkpoint_basename``); verified on disk in Phase 0.5.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Optional

from . import paths


def checkpoint_dir(project: str, config: dict[str, Any]) -> Path:
    """Project-level checkpoint directory, honoring ``config.checkpoint.directory``."""
    ck = config.get("checkpoint") or {}
    rel = str(ck.get("directory") or "checkpoints").strip() or "checkpoints"
    proj = paths.project_dir(project).resolve()
    path = (proj / rel).resolve()
    if proj not in path.parents and path != proj:
        path = proj / "checkpoints"
    return path


def stage_basename(config: dict[str, Any], stage: dict[str, Any]) -> str:
    """Filename stem the trainer uses for a stage's checkpoint (e.g. ``ppo_walk``)."""
    ck = config.get("checkpoint") or {}
    template = str(ck.get("filename_template") or "ppo_{stage_id}")
    stage_id = stage.get("id", "final")
    name = template.replace("{stage_id}", str(stage_id))
    return re.sub(r"[^\w\-]+", "_", name).strip("_") or "ppo_final"


def locate_stage_ckpt(project: str, stage: dict[str, Any], config: dict[str, Any]) -> Optional[Path]:
    """The stage's final checkpoint (``<basename>.zip``), or None if it doesn't exist yet."""
    p = checkpoint_dir(project, config) / f"{stage_basename(config, stage)}.zip"
    return p if p.is_file() else None


def capture_stage_ckpt(
    project: str, stage: dict[str, Any], config: dict[str, Any], dest: Path
) -> Optional[Path]:
    """Copy a just-finished trial's stage checkpoint to ``dest`` (before the next trial
    overwrites it). Returns the destination, or None if no checkpoint was produced."""
    src = locate_stage_ckpt(project, stage, config)
    if src is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def promote_best(captured: Path, dest: Path) -> Path:
    """Copy the winning trial's captured checkpoint to the frozen per-stage seed path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(captured, dest)
    return dest


def cleanup_trial_ckpts(stage_dir: Path, keep: Optional[Path] = None) -> None:
    """Delete per-trial checkpoint copies under ``stage_dir`` (keeping ``keep`` if given)."""
    keep_name = keep.name if keep else None
    for f in stage_dir.glob("trial_*_ckpt.zip"):
        if f.name == keep_name:
            continue
        try:
            f.unlink()
        except OSError:
            pass
