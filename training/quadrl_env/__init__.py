"""Quadruped RL environment — loads QuadRL editor exports for SB3 training."""
from quadrl_env.env_factory import make_quadruped_env, resolve_sim_backend
from quadrl_env.project_config import load_project_artifacts

__all__ = ["load_project_artifacts", "make_quadruped_env", "resolve_sim_backend"]
