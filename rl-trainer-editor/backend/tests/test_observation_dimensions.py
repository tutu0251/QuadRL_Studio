"""Observation vector dimension helpers."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import ObservationTerm
from planner.observation_dimensions import field_dim, term_dim, vector_breakdown


def _proc(tid: str, *, category: str = "state", kind: str = "joint_state") -> ObservationTerm:
    return ObservationTerm(
        id=tid,
        source="procedural",
        kind=kind,
        category=category,
        label=tid,
        enabled=True,
        available=True,
        key=tid,
    )


def test_joint_term_dims():
    t = _proc("joint_positions")
    assert term_dim(t, n_joints=12) == 12


def test_commands_dim():
    t = _proc("commands", category="command", kind="command")
    assert term_dim(t, n_joints=12) == 5


def test_imu_sensor_dim():
    t = ObservationTerm(
        id="sensor:imu",
        source="sensor",
        kind="imu",
        category="sensor",
        label="imu",
        enabled=True,
        available=True,
        key="base_imu",
        fields=["angular_velocity", "linear_acceleration"],
    )
    assert term_dim(t, n_joints=12) == 6


def test_field_dim_imu_and_contact():
    assert field_dim("imu", "angular_velocity") == 3
    assert field_dim("contact", "contacts") == 1
    assert field_dim("odom", "linear_velocity_x") == 1


def test_odom_sensor_dim_three_fields():
    t = ObservationTerm(
        id="sensor:odom",
        source="sensor",
        kind="odom",
        category="sensor",
        label="odom",
        enabled=True,
        available=True,
        key="base_odom",
        fields=["linear_velocity_x", "linear_velocity_y", "angular_velocity_z"],
    )
    assert term_dim(t, n_joints=12) == 3


def test_odom_sensor_dim_two_fields():
    t = ObservationTerm(
        id="sensor:odom",
        source="sensor",
        kind="odom",
        category="sensor",
        label="odom",
        enabled=True,
        available=True,
        key="base_odom",
        fields=["linear_velocity_x", "angular_velocity_z"],
    )
    assert term_dim(t, n_joints=12) == 2


def test_imu_partial_fields_dim():
    t = ObservationTerm(
        id="sensor:imu",
        source="sensor",
        kind="imu",
        category="sensor",
        label="imu",
        enabled=True,
        available=True,
        key="base_imu",
        fields=["angular_velocity"],
    )
    assert term_dim(t, n_joints=12) == 3


def test_vector_breakdown_offsets():
    terms = [
        _proc("joint_positions"),
        _proc("commands", category="command", kind="command"),
    ]
    out = vector_breakdown(terms, n_joints=4)
    assert out["totalDim"] == 9
    segs = out["segments"]
    assert segs[0]["startIndex"] == 0 and segs[0]["dim"] == 4
    assert segs[1]["startIndex"] == 4 and segs[1]["dim"] == 5
