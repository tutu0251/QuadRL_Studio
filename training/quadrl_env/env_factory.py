"""Factory for quadruped training environments."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from quadrl_env.project_config import load_project_artifacts
from quadrl_env.quadruped_env import QuadrupedEnv
from quadrl_env.ros_sim import ros_stack_available


def resolve_sim_backend(project_dir: Path, *, prefer: str | None = None) -> str:
    """Return 'ros' or 'mock'. prefer: auto|mock|ros."""
    mode = (prefer or os.environ.get("QUADRL_SIM_BACKEND", "auto")).lower()
    if mode == "mock":
        return "mock"
    if mode == "ros":
        return "ros"
    artifacts = load_project_artifacts(project_dir)
    if artifacts.workspace_setup and ros_stack_available():
        return "ros"
    return "mock"


def make_quadruped_env(
    project_dir: Path,
    config: dict[str, Any] | None = None,
    *,
    stage: dict[str, Any] | None = None,
    env_id: int = 0,
    backend: str | None = None,
) -> QuadrupedEnv:
    artifacts = load_project_artifacts(project_dir, rl_config=config)
    resolved = backend or resolve_sim_backend(project_dir)
    if resolved == "ros" and env_id > 0:
        resolved = "mock"
    return QuadrupedEnv(artifacts, stage=stage, backend=resolved, env_id=env_id)


def make_vec_env_fn(
    project_dir: Path,
    config: dict[str, Any],
    *,
    stage: dict[str, Any] | None = None,
    env_id: int = 0,
    backend: str | None = None,
) -> Callable[[], QuadrupedEnv]:
    def _init() -> QuadrupedEnv:
        return make_quadruped_env(
            project_dir,
            config,
            stage=stage,
            env_id=env_id,
            backend=backend,
        )

    return _init
