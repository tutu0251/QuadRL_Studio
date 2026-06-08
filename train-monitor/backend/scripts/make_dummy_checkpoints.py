#!/usr/bin/env python3
"""Generate dummy SB3-style checkpoints for UI/feature testing.

These are NOT trainable models — each is a minimal zip carrying a JSON ``data``
member with a ``num_timesteps`` field (the only thing the monitor reads to
decide mid-stage vs. completed resume) plus a placeholder ``policy.pth``. They
let you exercise the two resume modes in train-monitor without running a real
training job:

  * "Continue from checkpoint" — the filename maps back to a curriculum stage and
    ``num_timesteps`` decides whether that stage is mid-run or complete.
  * "Start from stage" — any checkpoint works as a weight seed for the chosen
    stage (the stage index is explicit, so the filename is irrelevant).

Real SB3 ``model.load()`` will reject these, so use dry-run mode (or just inspect
the built command) when you actually launch training.

Usage:
    python3 scripts/make_dummy_checkpoints.py                 # all curriculum projects
    python3 scripts/make_dummy_checkpoints.py my_robot        # one or more projects
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

# Make sibling packages importable when run directly from scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from storage import project_storage  # noqa: E402


def _checkpoint_basename(config: dict, stage: dict) -> str:
    """Mirror run_rl_train._checkpoint_basename for the default template."""
    ckpt = config.get("checkpoint") or {}
    template = str(ckpt.get("filename_template", "ppo_{stage_id}"))
    return template.replace("{stage_id}", str(stage.get("id", "final")))


def _write_dummy(path: Path, num_timesteps: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("data", json.dumps({"num_timesteps": num_timesteps}))
        zf.writestr("policy.pth", b"dummy-weights")
    print(f"  wrote {path.name}  (num_timesteps={num_timesteps:,})")


def make_for_project(name: str) -> bool:
    rl_path = project_storage.rl_config_path(name)
    if not rl_path.is_file():
        print(f"[skip] {name}: missing {rl_path.name}")
        return False
    config = yaml.safe_load(rl_path.read_text()) or {}
    curriculum = config.get("curriculum") or {}
    stages = curriculum.get("stages") or []
    if not (curriculum.get("enabled") and stages):
        print(f"[skip] {name}: no enabled curriculum")
        return False

    ckpt_dir = project_storage.checkpoints_dir(name)
    print(f"[{name}] -> {ckpt_dir}")

    # Stage 0 fully trained: "Continue" advances into stage 1 (seeded).
    s0 = stages[0]
    _write_dummy(
        ckpt_dir / f"{_checkpoint_basename(config, s0)}.zip",
        int(s0.get("timesteps", 100_000)),
    )

    # A middle stage, completed: "Continue" advances to the following stage.
    mid_i = min(2, len(stages) - 1)
    s_mid = stages[mid_i]
    mid_budget = int(s_mid.get("timesteps", 100_000))
    _write_dummy(ckpt_dir / f"{_checkpoint_basename(config, s_mid)}.zip", mid_budget)

    # Same middle stage, periodic mid-run save: "Continue" resumes it in place.
    _write_dummy(
        ckpt_dir / f"{_checkpoint_basename(config, s_mid)}_{mid_budget // 2}_steps.zip",
        mid_budget // 2,
    )

    # Foreign/pretrained seed with no stage id: "Continue" seeds stage 1 fresh;
    # ideal for testing "Start from stage" against an arbitrary stage.
    _write_dummy(ckpt_dir / "best_model.zip", 250_000)
    return True


def main(argv: list[str]) -> int:
    targets = argv[1:] or project_storage.list_projects()
    made_any = False
    for name in targets:
        made_any |= make_for_project(name)
    if not made_any:
        print("No curriculum projects found — nothing generated.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
