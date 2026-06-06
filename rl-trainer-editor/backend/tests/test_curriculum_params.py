"""Regression tests pinning the bent-pose tuned curriculum parameters.

These lock in the values documented in PARAMETER_FIXES_SUMMARY.md so the
"verified" claim is actually backed by tests and cannot silently drift. In
particular they guard against the failure mode where a template value is
overwritten by recommend_stage_params (the live source), making a documented
change dead code.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planner.curriculum_templates import build_stand_sprint_curriculum
from planner.standing_heights import PLACEHOLDER_BODY_HEIGHT_M


def _by_id(cur):
    return {s.id: s for s in cur.stages}


def test_velocity_ladder_strictly_increases_and_gallop_is_fastest():
    s = _by_id(build_stand_sprint_curriculum())
    vels = [s[k].command.targetLinVelX for k in ("walk", "trot", "pace", "bound", "gallop")]
    assert vels == sorted(vels)
    assert len(set(vels)) == len(vels)  # strictly increasing — no ties
    # Gallop is the final/fastest gait; must outrun bound (the #4 regression).
    assert s["gallop"].command.targetLinVelX > s["bound"].command.targetLinVelX
    assert s["gallop"].command.targetLinVelX == 1.4


def test_body_height_target_is_bent_pose_everywhere():
    for stage in build_stand_sprint_curriculum().stages:
        assert stage.command.targetBodyHeight == PLACEHOLDER_BODY_HEIGHT_M


def test_tilt_progression_matches_recommender_and_caps_at_1_2():
    cur = build_stand_sprint_curriculum()
    for stage in cur.stages:
        assert stage.termination.maxTiltRad == min(1.2, 0.75 + stage.order * 0.06)
    assert cur.stages[-1].termination.maxTiltRad <= 1.2


def test_episode_length_progression():
    for stage in build_stand_sprint_curriculum().stages:
        assert stage.termination.maxEpisodeSteps == 800 + stage.order * 200


def test_advance_criteria_tightened():
    for stage in build_stand_sprint_curriculum().stages:
        o = stage.order
        a = stage.advanceCriteria
        assert a.minMeanEpisodeReward == max(0.25, 0.65 - o * 0.06)
        assert a.minEpisodeLengthFrac == max(0.65, 0.90 - o * 0.04)
        assert a.maxFallRate == min(0.20, 0.08 + o * 0.02)


def test_flat_terrain_has_no_disturbance():
    for stage in build_stand_sprint_curriculum(rough=False).stages:
        assert stage.disturbance.enabled is False


def test_rough_disturbance_is_actually_reduced():
    # Regression for the dead-code bug: the recommender (not the template) is the
    # live source, and must emit the conservative reduced formulas at runtime.
    cur = build_stand_sprint_curriculum(rough=True)
    for stage in cur.stages:
        roughness = min(0.85, 0.15 + stage.order * 0.1)
        d = stage.disturbance
        assert d.enabled is True
        assert d.pushForceN == 10 + roughness * 25
        assert d.pushIntervalSteps == max(300, int(800 - roughness * 300))
        assert d.terrainRoughness == roughness * 0.8
        assert d.lateralImpulseN == 5 + roughness * 12
        assert d.randomOrientationNoiseRad == 0.02 + roughness * 0.05
    # Magnitude must be below the old aggressive values (push was 15 + r*30,
    # terrain == roughness). Gallop's old live push force was 37.5 N.
    gallop = _by_id(cur)["gallop"].disturbance
    assert gallop.pushForceN < 30.0
    assert gallop.terrainRoughness < min(0.85, 0.15 + 6 * 0.1)
