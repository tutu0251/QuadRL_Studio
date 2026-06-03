"""Tests for disturbance engine."""
from __future__ import annotations

import numpy as np

from quadrl_env.disturbances import DisturbanceEngine


def test_disturbance_disabled_no_wrench():
    eng = DisturbanceEngine({"enabled": False, "push_force_n": 50})
    eng.reset(seed=0)
    assert eng.ros_wrench() is None


def test_disturbance_enabled_applies_wrench():
    eng = DisturbanceEngine({"enabled": True, "push_force_n": 100, "push_interval_steps": 1})
    eng.reset(seed=1)
    wrench = eng.ros_wrench()
    assert wrench is not None
    force, torque = wrench
    assert float(np.linalg.norm(force)) > 0.0
    assert torque.shape == (3,)
