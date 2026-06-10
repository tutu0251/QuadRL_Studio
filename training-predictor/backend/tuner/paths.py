"""Filesystem conventions shared with the rest of QuadRL Studio.

Mirrors the editors' ``project_storage`` (``Path.home()/quadruped_dev_tool/projects``)
and the training launcher location, with environment overrides so the module can
run unchanged on a different machine layout.
"""
from __future__ import annotations

import os
from pathlib import Path


def projects_root() -> Path:
    """Root holding ``<project>/exports/...`` — overridable via QUADRL_PROJECTS_DIR
    (the same env var train-monitor honours)."""
    env = os.environ.get("QUADRL_PROJECTS_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / "quadruped_dev_tool" / "projects"


def project_dir(project: str) -> Path:
    return projects_root() / project


def base_rl_config(project: str) -> Path:
    return project_dir(project) / "exports" / f"rl_{project}_config.yaml"


def base_ppo_config(project: str) -> Path:
    return project_dir(project) / "exports" / f"ppo_{project}_config.yaml"


def tuning_root(project: str) -> Path:
    return project_dir(project) / "tuning"


def list_projects() -> list[str]:
    root = projects_root()
    if not root.exists():
        return []
    out = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and (p / "exports" / f"rl_{p.name}_config.yaml").exists():
            out.append(p.name)
    return out
