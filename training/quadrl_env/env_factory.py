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
    ros_domain_id: int | None = None,
) -> Callable[[], QuadrupedEnv]:
    def _init() -> QuadrupedEnv:
        # When parallel, each env runs in its own process (SubprocVecEnv); isolate it on
        # two independent transport layers. Both must be set before rclpy.init and the
        # Gazebo launch (which inherit this process' env):
        #   1. ROS_DOMAIN_ID — isolates the ROS 2 / DDS graph (/joint_states,
        #      /controller_manager, the ros_gz service names).
        #   2. IGN_PARTITION / GZ_PARTITION — isolates Gazebo's own ign-transport graph.
        #      ROS_DOMAIN_ID does NOT reach it, and every env uses the same world name,
        #      so without a partition the ros_gz bridges would cross-wire one server's
        #      gz topics (e.g. /world/flat/pose/info) into another env's ROS state.
        if ros_domain_id is not None:
            os.environ["ROS_DOMAIN_ID"] = str(ros_domain_id)
            partition = f"quadrl_{ros_domain_id}"
            os.environ["IGN_PARTITION"] = partition  # Fortress / ign-transport
            os.environ["GZ_PARTITION"] = partition  # newer gz-transport alias
            # Give each env its own ign-common log dir (default is the shared
            # ~/.ignition); concurrent servers otherwise write auto_default.log into
            # the same directory. IGN_LOG_PATH is read by ignition-common (Fortress);
            # GZ_LOG_PATH is the newer alias.
            log_dir = project_dir / "gazebo_logs" / partition
            log_dir.mkdir(parents=True, exist_ok=True)
            os.environ["IGN_LOG_PATH"] = str(log_dir)
            os.environ["GZ_LOG_PATH"] = str(log_dir)
        return make_quadruped_env(
            project_dir,
            config,
            stage=stage,
            env_id=env_id,
        )

    return _init
