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


def test_standing_height_params_trunk_centre():
    # After the root-origin bake fix base_link sits at the trunk centre, so a
    # robot's grounded standing height is positive (e.g. 0.2933 m for the standard
    # quadruped) -> fall 0.1933 m. (This replaces the old below-ground -0.0417 case.)
    h = standing_height_params(0.2933)
    assert h.target_body_height == 0.2933
    assert h.fall_base_height_threshold == pytest.approx(0.1933, abs=1e-4)
    assert h.fall_base_height_threshold < h.target_body_height


def test_standing_height_params_does_not_clamp_negative():
    # Defensive: standing_height_params must pass a degenerate below-origin spawn
    # through unchanged (no clamping). Real robots don't produce this anymore.
    h = standing_height_params(-0.05)
    assert h.target_body_height == -0.05
    assert h.fall_base_height_threshold == pytest.approx(-0.15, abs=1e-4)
