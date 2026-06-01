"""Project storage — shared paths under ~/quadruped_dev_tool/projects."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from domain.models import CheckpointInfo

PROJECTS_ROOT = Path(os.environ.get("QUADRL_PROJECTS_DIR", Path.home() / "quadruped_dev_tool" / "projects"))
EXPORTS_DIR = "exports"
CHECKPOINTS_DIR = "checkpoints"
RUNS_DIR = "runs"

REQUIRED_EXPORTS = (
    "rl_{name}_config.yaml",
    "ppo_{name}_config.yaml",
)


def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def exports_dir(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR


def checkpoints_dir(name: str, directory: str = CHECKPOINTS_DIR) -> Path:
    return project_dir(name) / directory


def runs_dir(name: str) -> Path:
    return project_dir(name) / RUNS_DIR


def rl_config_path(name: str) -> Path:
    return exports_dir(name) / f"rl_{name}_config.yaml"


def ppo_config_path(name: str) -> Path:
    return exports_dir(name) / f"ppo_{name}_config.yaml"


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(
        p.name
        for p in PROJECTS_ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def list_checkpoints(name: str, directory: str = CHECKPOINTS_DIR) -> list[CheckpointInfo]:
    ckpt_dir = checkpoints_dir(name, directory)
    if not ckpt_dir.is_dir():
        return []
    root = project_dir(name)
    out: list[CheckpointInfo] = []
    for p in sorted(ckpt_dir.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = p.stat()
        rel = str(p.relative_to(root))
        out.append(
            CheckpointInfo(
                path=rel,
                filename=p.name,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )
    return out


def has_rl_export(name: str) -> bool:
    return rl_config_path(name).is_file()


def has_ppo_export(name: str) -> bool:
    return ppo_config_path(name).is_file()
