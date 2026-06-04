"""Tests for symmetric random spawn pose sampling."""
from __future__ import annotations

import numpy as np

from quadrl_env.project_config import SpawnOffset, sample_spawn_pose


def test_sample_within_symmetric_bounds() -> None:
    base = {"x": 1.0, "y": 2.0, "z": 0.5, "roll": 0.0, "pitch": 0.0, "yaw": 0.0}
    offset = SpawnOffset(dx=0.1, dy=0.2, dz=0.05, droll=0.01, dpitch=0.02, dyaw=0.03)
    rng = np.random.default_rng(42)
    for _ in range(200):
        pose = sample_spawn_pose(base, offset, rng=rng)
        assert 0.9 <= pose["x"] <= 1.1
        assert 1.8 <= pose["y"] <= 2.2
        assert 0.45 <= pose["z"] <= 0.55
        assert -0.01 <= pose["roll"] <= 0.01
        assert -0.02 <= pose["pitch"] <= 0.02
        assert -0.03 <= pose["yaw"] <= 0.03


def test_epsilon_fallback_when_offset_near_zero() -> None:
    base = {"x": 0.0, "y": 0.0, "z": 0.5, "roll": 0.0, "pitch": 0.0, "yaw": 0.0}
    offset = SpawnOffset()
    rng = np.random.default_rng(0)
    pose = sample_spawn_pose(base, offset, rng=rng)
    assert -0.02 <= pose["x"] <= 0.02
    assert -0.02 <= pose["y"] <= 0.02
    assert 0.49 <= pose["z"] <= 0.51
