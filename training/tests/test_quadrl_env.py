"""Unit tests for quadruped env (mock backend, no ROS)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(REPO / "training"))

from quadrl_env.env_factory import make_quadruped_env
from quadrl_env.observations import ObservationBuilder
from quadrl_env.project_config import load_project_artifacts
from quadrl_env.rewards import RewardEngine
from quadrl_env.sim_state import SimState


def _write_minimal_project(root: Path, name: str) -> Path:
    exports = root / "exports"
    exports.mkdir(parents=True)
    (exports / f"ctrl_{name}_controllers.yaml").write_text(
        "joint_trajectory_controller:\n  ros__parameters:\n    joints: [j1, j2, j3]\n",
        encoding="utf-8",
    )
    (exports / f"ctrl_{name}_gains.yaml").write_text(
        "joints:\n  j1:\n    kp: 20\n    kd: 0.5\n    default_position: 0.0\n    action_scale: 0.2\n",
        encoding="utf-8",
    )
    (exports / f"sens_{name}_observations.yaml").write_text(
        f"""robot_name: {name}
observations:
  imu:
    kind: imu
    topic: /{name}/imu
    fields: [angular_velocity]
""",
        encoding="utf-8",
    )
    rl = {
        "algorithm": "PPO",
        "observations": {
            "terms": [
                {"id": "joint_positions", "enabled": True, "available": True, "scale": 2.0, "clip_min": -1, "clip_max": 1},
                {"id": "commands", "enabled": True, "available": True, "scale": 1.0},
            ]
        },
        "task": {
            "reward_terms": [
                {"id": "alive", "type": "reward", "enabled": True, "weight": 0.25, "params": {}},
                {"id": "forward_tracking", "type": "reward", "enabled": True, "weight": 1.0, "params": {"sigma": 0.2}},
            ],
            "termination": {"max_episode_steps": 50, "fall_base_height_threshold": 0.1, "max_tilt_rad": 1.5},
        },
        "command": {"target_lin_vel_x": 0.5, "target_body_height": 0.35},
    }
    (exports / f"rl_{name}_config.yaml").write_text(yaml.dump(rl), encoding="utf-8")
    return root


def test_observation_builder_dim():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _write_minimal_project(Path(tmp) / "bot", "bot")
        artifacts = load_project_artifacts(proj)
        builder = ObservationBuilder(artifacts.rl_config, artifacts.observations_doc, artifacts.joint_names)
        assert builder.observation_dim == 3 + 5


def test_reward_engine_positive_on_tracking():
    state = SimState(
        joint_pos=np.zeros(3),
        joint_vel=np.zeros(3),
        base_lin_vel=np.array([0.5, 0.0, 0.0]),
        base_ang_vel=np.zeros(3),
        projected_gravity=np.array([0.0, 0.0, -1.0]),
        base_height=0.35,
    )
    terms = [
        {"id": "forward_tracking", "type": "reward", "enabled": True, "weight": 1.0, "params": {"sigma": 0.2}},
    ]
    total, _ = RewardEngine(terms).compute(state, command={"target_lin_vel_x": 0.5}, action=np.zeros(3), last_action=np.zeros(3))
    assert total > 0.5


def test_quadruped_env_episode():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _write_minimal_project(Path(tmp) / "bot", "bot")
        env = make_quadruped_env(proj, backend="mock")
        obs, info = env.reset()
        assert obs.shape == env.observation_space.shape
        obs2, reward, term, trunc, info2 = env.step(env.action_space.sample())
        assert obs2.shape == obs.shape
        assert isinstance(reward, float)
        env.close()
