"""Unit tests for quadruped env (mock backend, no ROS)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(REPO / "training"))

from quadrl_env.env_factory import make_quadruped_env
from quadrl_env.observations import ObservationBuilder
from quadrl_env.project_config import load_project_artifacts
from quadrl_env.rewards import RewardEngine
from quadrl_env.sensor_packing import fit_dim, pack_imu, pack_odom, sensor_term_dim
from quadrl_env.sim_state import SimState
from quadrl_env.termination import TerminationEngine


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


def test_termination_skips_null_max_joint_torque():
    engine = TerminationEngine(
        {
            "max_episode_steps": 1000,
            "fall_base_height_threshold": 0.05,
            "max_tilt_rad": 2.0,
            "max_joint_torque": None,
        }
    )
    state = SimState(
        joint_pos=np.zeros(12),
        joint_vel=np.full(12, 100.0),
        base_lin_vel=np.zeros(3),
        base_ang_vel=np.zeros(3),
        projected_gravity=np.array([0.0, 0.0, -1.0]),
        base_height=0.35,
        episode_step=10,
    )
    terminated, truncated, reason = engine.check(state, step_reward=0.0, cumulative_reward=0.0)
    assert not terminated
    assert not truncated
    assert reason == ""


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


def test_sensor_term_fits_declared_dim_when_vector_wrong_length():
    rl_config = {
        "observations": {
            "terms": [
                {
                    "id": "sensor:imu",
                    "source": "sensor",
                    "kind": "imu",
                    "enabled": True,
                    "available": True,
                    "key": "base_imu",
                    "fields": ["angular_velocity", "linear_acceleration", "orientation"],
                    "scale": 1.0,
                }
            ]
        }
    }
    obs_doc = {"observations": {"base_imu": {"kind": "imu", "fields": ["angular_velocity", "linear_acceleration", "orientation"]}}}
    builder = ObservationBuilder(rl_config, obs_doc, ["j1", "j2"])
    assert builder.observation_dim == 9

    state = SimState(
        joint_pos=np.zeros(2),
        joint_vel=np.zeros(2),
        base_lin_vel=np.zeros(3),
        base_ang_vel=np.zeros(3),
        projected_gravity=np.array([0.0, 0.0, -1.0]),
        base_height=0.35,
    )
    wrong = builder.build(state, command={}, last_action=np.zeros(2), sensor_vectors={"base_imu": np.ones(3, dtype=np.float32)})
    full = builder.build(
        state,
        command={},
        last_action=np.zeros(2),
        sensor_vectors={
            "base_imu": pack_imu(
                ["angular_velocity", "linear_acceleration", "orientation"],
                angular_velocity=np.array([1.0, 0.0, 0.0]),
                linear_acceleration=np.array([0.0, 0.0, -9.8]),
                orientation=np.array([0.0, 0.0, 0.0]),
            )
        },
    )
    assert wrong.shape == (9,)
    assert full.shape == (9,)


def test_imu_packing_nine_dims():
    vec = pack_imu(
        ["angular_velocity", "linear_acceleration", "orientation"],
        angular_velocity=np.array([1.0, 2.0, 3.0]),
        linear_acceleration=np.array([4.0, 5.0, 6.0]),
        orientation=np.array([7.0, 8.0, 9.0]),
    )
    assert vec.shape == (9,)
    assert vec[0] == 1.0
    assert vec[3] == 4.0
    assert vec[6] == 7.0


def test_odom_packing_three_scalars():
    vec = pack_odom(
        ["linear_velocity_x", "linear_velocity_y", "angular_velocity_z"],
        linear_velocity_x=0.5,
        linear_velocity_y=-0.1,
        angular_velocity_z=0.2,
    )
    assert vec.shape == (3,)
    assert vec[0] == pytest.approx(0.5)
    assert vec[1] == pytest.approx(-0.1)
    assert vec[2] == pytest.approx(0.2)
    assert sensor_term_dim("odom", ["linear_velocity_x", "linear_velocity_y", "angular_velocity_z"]) == 3


def test_my_robot_like_observation_dim_is_66():
    n_joints = 12
    terms = [
        {"id": "joint_positions", "source": "procedural", "enabled": True, "available": True},
        {"id": "joint_velocities", "source": "procedural", "enabled": True, "available": True},
        {"id": "last_actions", "source": "procedural", "enabled": True, "available": True},
        {"id": "commands", "source": "procedural", "enabled": True, "available": True},
        {"id": "base_lin_vel", "source": "procedural", "enabled": True, "available": True},
        {"id": "base_ang_vel", "source": "procedural", "enabled": True, "available": True},
        {"id": "projected_gravity", "source": "procedural", "enabled": True, "available": True},
        {
            "id": "sensor:imu",
            "source": "sensor",
            "kind": "imu",
            "enabled": True,
            "available": True,
            "key": "base_link_imu",
            "fields": ["angular_velocity", "linear_acceleration", "orientation"],
        },
        *[
            {
                "id": f"sensor:foot_{i}",
                "source": "sensor",
                "kind": "contact",
                "enabled": True,
                "available": True,
                "key": f"foot_{i}",
                "fields": ["contacts"],
            }
            for i in range(4)
        ],
        {
            "id": "sensor:odom",
            "source": "sensor",
            "kind": "odom",
            "enabled": True,
            "available": True,
            "key": "base_link_odom",
            "fields": ["linear_velocity_x", "linear_velocity_y", "angular_velocity_z"],
        },
    ]
    obs_doc = {"observations": {}}
    builder = ObservationBuilder({"observations": {"terms": terms}}, obs_doc, [f"j{i}" for i in range(n_joints)])
    assert builder.observation_dim == 66
    assert sensor_term_dim("imu", ["angular_velocity", "linear_acceleration", "orientation"]) == 9
    assert fit_dim(np.ones(3), 9).shape == (9,)


def test_quadruped_env_obs_stable_with_populated_sensors():
    rl_config = {
        "observations": {
            "terms": [
                {"id": "joint_positions", "enabled": True, "available": True, "scale": 1.0},
                {
                    "id": "sensor:imu",
                    "source": "sensor",
                    "kind": "imu",
                    "enabled": True,
                    "available": True,
                    "key": "imu",
                    "fields": ["angular_velocity", "linear_acceleration", "orientation"],
                    "scale": 1.0,
                },
            ]
        },
        "task": {"reward_terms": [], "termination": {"max_episode_steps": 10}},
    }
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "bot"
        exports = proj / "exports"
        exports.mkdir(parents=True)
        (exports / "ctrl_bot_controllers.yaml").write_text(
            "joint_trajectory_controller:\n  ros__parameters:\n    joints: [j1, j2, j3]\n",
            encoding="utf-8",
        )
        (exports / "ctrl_bot_gains.yaml").write_text(
            "joints:\n  j1:\n    kp: 20\n    kd: 0.5\n    default_position: 0.0\n    action_scale: 0.2\n",
            encoding="utf-8",
        )
        (exports / "sens_bot_observations.yaml").write_text(
            "observations:\n  imu:\n    kind: imu\n    fields: [angular_velocity, linear_acceleration, orientation]\n",
            encoding="utf-8",
        )
        (exports / "rl_bot_config.yaml").write_text(yaml.dump(rl_config), encoding="utf-8")
        env = make_quadruped_env(proj, backend="mock")
        obs0, _ = env.reset()
        assert obs0.shape == (12,)
        obs1, _, _, _, _ = env.step(env.action_space.sample())
        assert obs1.shape == (12,)
        env.close()
