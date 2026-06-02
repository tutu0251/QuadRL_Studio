"""Factory for quadruped training environments."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from quadrl_env.project_config import load_project_artifacts
from quadrl_env.quadruped_env import QuadrupedEnv
from quadrl_env.ros_sim import ros_stack_available


def resolve_sim_backend(project_dir: Path, *, prefer: str | None = None) -> str:
    """Return 'ros' when workspace and rclpy are available; otherwise raise."""
    mode = (prefer or os.environ.get("QUADRL_SIM_BACKEND", "auto")).lower()
    if mode == "mock":
        raise ValueError(
            "Mock simulation backend has been removed. Build the project workspace and use 'ros'."
        )
    if mode not in ("auto", "ros"):
        raise ValueError(f"Unknown sim backend {mode!r}; use 'auto' or 'ros'.")

    artifacts = load_project_artifacts(project_dir)
    if not artifacts.workspace_setup:
        raise RuntimeError(
            "ROS simulation requires a built workspace at "
            f"{project_dir / 'workspace' / 'install' / 'setup.bash'}"
        )
    if not ros_stack_available(workspace_setup=artifacts.workspace_setup):
        raise RuntimeError(
            "ROS stack unavailable. Install ROS 2 Humble, build the project workspace, "
            "and ensure rclpy imports."
        )
    return "ros"


def make_quadruped_env(
    project_dir: Path,
    config: dict[str, Any] | None = None,
    *,
    stage: dict[str, Any] | None = None,
    env_id: int = 0,
) -> QuadrupedEnv:
    artifacts = load_project_artifacts(project_dir, rl_config=config)
    resolve_sim_backend(project_dir)
    return QuadrupedEnv(artifacts, stage=stage, env_id=env_id)


def make_vec_env_fn(
    project_dir: Path,
    config: dict[str, Any],
    *,
    stage: dict[str, Any] | None = None,
    env_id: int = 0,
) -> Callable[[], QuadrupedEnv]:
    def _init() -> QuadrupedEnv:
        return make_quadruped_env(
            project_dir,
            config,
            stage=stage,
            env_id=env_id,
        )

    return _init
