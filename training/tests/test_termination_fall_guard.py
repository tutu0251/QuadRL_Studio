"""Guard tests: the fall-height threshold must follow the robot's real spawn
height, so a leaked placeholder standing height can't terminate every episode on
step 1 (the failure where reason=fall_height fires at steps=1 forever)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quadrl_env.sim_state import SimState
from quadrl_env.standing_heights import FALL_DROP_MARGIN_M
from quadrl_env.termination import TerminationEngine


def _upright_state(base_height: float) -> SimState:
    n = 4
    return SimState(
        joint_pos=np.zeros(n, dtype=np.float32),
        joint_vel=np.zeros(n, dtype=np.float32),
        base_lin_vel=np.zeros(3, dtype=np.float32),
        base_ang_vel=np.zeros(3, dtype=np.float32),
        projected_gravity=np.array([0.0, 0.0, -1.0], dtype=np.float32),  # upright -> tilt 0
        base_height=base_height,
        episode_step=0,
    )


def test_sane_threshold_is_kept():
    eng = TerminationEngine({"fall_base_height_threshold": -0.1417})
    info = eng.resolve_fall_threshold(-0.0417)
    assert info["corrected"] is False
    assert info["effective"] == -0.1417


def test_placeholder_leak_above_spawn_is_corrected():
    # The real bug: threshold 0.1933 (0.2933 placeholder - margin) sits ABOVE the
    # robot's -0.0417 spawn height, so it would "fall" before moving.
    eng = TerminationEngine({"fall_base_height_threshold": 0.1933})
    info = eng.resolve_fall_threshold(-0.0417)
    assert info["corrected"] is True
    assert info["effective"] == round(-0.0417 - FALL_DROP_MARGIN_M, 4)  # -0.1417


def test_missing_threshold_derived_from_standing_height():
    eng = TerminationEngine({})
    info = eng.resolve_fall_threshold(0.30)
    assert info["effective"] == round(0.30 - FALL_DROP_MARGIN_M, 4)
    assert info["corrected"] is False


def test_none_standing_height_keeps_configured():
    eng = TerminationEngine({"fall_base_height_threshold": -0.1417})
    info = eng.resolve_fall_threshold(None)
    assert info["effective"] == -0.1417
    assert info["corrected"] is False


def test_robot_at_spawn_does_not_instantly_fall_after_guard():
    # End-to-end: with the leaked placeholder threshold, the robot at its real
    # spawn height must NOT be declared fallen on step 1 once the guard is applied.
    eng = TerminationEngine({"fall_base_height_threshold": 0.1933, "max_episode_steps": 100})
    state = _upright_state(-0.0417)

    # Before anchoring, the leaked threshold would (wrongly) terminate.
    terminated, _, reason = eng.check(state, step_reward=0.0, cumulative_reward=0.0,
                                      command={"target_body_height": -0.0417})
    assert terminated and reason == "fall_height"

    # After anchoring to the real spawn height, no instant fall.
    eng.resolve_fall_threshold(-0.0417)
    terminated, _, reason = eng.check(state, step_reward=0.0, cumulative_reward=0.0,
                                      command={"target_body_height": -0.0417})
    assert reason != "fall_height"
    assert not terminated
