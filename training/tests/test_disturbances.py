"""Tests for disturbance engine."""
from __future__ import annotations

import numpy as np

from quadrl_env.disturbances import DisturbanceEngine
from quadrl_env.sim_state import SimState


def _state() -> SimState:
    return SimState(
        joint_pos=np.zeros(3, dtype=np.float32),
        joint_vel=np.zeros(3, dtype=np.float32),
        base_lin_vel=np.zeros(3, dtype=np.float32),
        base_ang_vel=np.zeros(3, dtype=np.float32),
        projected_gravity=np.array([0.0, 0.0, -1.0], dtype=np.float32),
        base_height=0.35,
    )


def test_disturbance_disabled_no_push():
    eng = DisturbanceEngine({"enabled": False, "push_force_n": 50})
    eng.reset(seed=0)
    before = _state()
    after = eng.apply_mock(before)
    assert np.allclose(after.base_lin_vel, before.base_lin_vel)


def test_disturbance_enabled_applies_push():
    eng = DisturbanceEngine({"enabled": True, "push_force_n": 100, "push_interval_steps": 1})
    eng.reset(seed=1)
    after = eng.apply_mock(_state())
    assert float(np.linalg.norm(after.base_lin_vel)) > 0.0
