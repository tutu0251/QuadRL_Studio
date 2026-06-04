"""Tests for spawn grounding helpers."""
from __future__ import annotations

import sys

import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.spawn_grounding import compute_grounded_spawn_z, compute_min_collision_z


def test_grounded_spawn_z_for_simple_leg(tmp_path: Path):
    urdf = tmp_path / "bot.urdf"
    urdf.write_text(
        """<?xml version="1.0"?>
<robot name="bot">
  <link name="base"/>
  <link name="foot">
    <collision>
      <origin xyz="0 0 0"/>
      <geometry><sphere radius="0.02"/></geometry>
    </collision>
  </link>
  <joint name="knee" type="fixed">
    <parent link="base"/>
    <child link="foot"/>
    <origin xyz="0 0 -0.4"/>
  </joint>
</robot>
"""
    )
    assert compute_min_collision_z(urdf) == pytest.approx(-0.42)
    assert compute_grounded_spawn_z(urdf) == pytest.approx(0.42)


def test_grounded_spawn_z_defaults_to_zero_without_collision(tmp_path: Path):
    urdf = tmp_path / "empty.urdf"
    urdf.write_text(
        """<?xml version="1.0"?>
<robot name="bot">
  <link name="base"/>
</robot>
"""
    )
    assert compute_min_collision_z(urdf) == 0.0
    assert compute_grounded_spawn_z(urdf) == 0.0
