"""Tests for reward/penalty catalog."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import StageCommand
from planner.reward_catalog import (
    REWARD_CATALOG,
    build_full_reward_catalog,
    locomotion_reward_terms,
    merge_reward_terms,
    stand_reward_terms,
)


def test_catalog_has_all_terms():
    reward_ids = {e.id for e in REWARD_CATALOG if e.type == "reward"}
    penalty_ids = {e.id for e in REWARD_CATALOG if e.type == "penalty"}
    assert reward_ids == {
        "alive",
        "upright",
        "height",
        "posture",
        "contact",
        "forward_tracking",
        "forward_progress",
        "lateral_tracking",
        "yaw_tracking",
        "diagonal_balance",
        "air_time",
        "foot_clearance",
    }
    assert penalty_ids == {
        "angular_velocity",
        "linear_velocity",
        "z_velocity",
        "joint_velocity",
        "action_velocity",
        "action_rate",
        "posture_penalty",
        "target_posture",
        "smoothness",
        "contact_balance",
        "contact_switch",
        "target_like",
        "stumble",
        "slip",
        "zmp",
    }


def test_full_catalog_length():
    terms = build_full_reward_catalog()
    assert len(terms) == len(REWARD_CATALOG)


def test_merge_maps_legacy_ids():
    from domain.models import RewardTerm

    legacy = [
        RewardTerm(
            id="lin_vel_tracking",
            type="reward",
            category="velocity",
            weight=1.0,
            enabled=True,
            params={"sigma": 0.2},
        )
    ]
    merged = merge_reward_terms(legacy)
    assert any(t.id == "forward_tracking" for t in merged)
    assert len(merged) == len(REWARD_CATALOG)


def test_stand_enables_subset():
    terms = stand_reward_terms()
    enabled = {t.id for t in terms if t.enabled}
    assert "height" in enabled
    assert "forward_tracking" not in enabled
    assert "linear_velocity" in enabled


def test_locomotion_enables_tracking():
    cmd = StageCommand(targetLinVelX=0.8, targetBodyHeight=0.36)
    terms = locomotion_reward_terms(0.8, cmd=cmd)
    enabled = {t.id for t in terms if t.enabled}
    assert "forward_tracking" in enabled
    height = next(t for t in terms if t.id == "height")
    assert height.params["target_height"] == 0.36
