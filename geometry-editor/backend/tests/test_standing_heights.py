"""Tests for standing height policy."""
from __future__ import annotations

import pytest

from domain.standing_heights import standing_height_params


def test_standing_height_params_positive_spawn():
    h = standing_height_params(0.42)
    assert h.spawn_z == 0.42
    assert h.target_body_height == h.spawn_z
    assert h.fall_base_height_threshold == pytest.approx(0.32, abs=1e-4)
    assert h.fall_base_height_threshold < h.target_body_height


def test_standing_height_params_negative_spawn():
    h = standing_height_params(-0.0417)
    assert h.target_body_height == -0.0417
    assert h.fall_base_height_threshold == pytest.approx(-0.1417, abs=1e-4)
    assert h.fall_base_height_threshold < h.target_body_height
