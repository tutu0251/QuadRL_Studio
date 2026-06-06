"""RL editor height recommendations follow shared policy."""
from __future__ import annotations

import pytest

from domain.models import CurriculumStage, TerminationConfig
from planner.recommender import recommend_stage_params
from planner.standing_heights import assert_height_policy_consistent, heights_for_target


def test_heights_for_target_matches_policy() -> None:
    # Trunk-centre standing height (base_link sits at the trunk after the geometry
    # root-origin bake fix): target 0.2933 m -> fall 0.1933 m.
    h = heights_for_target(0.2933)
    assert_height_policy_consistent(h)
    assert h.fall_base_height_threshold == pytest.approx(0.1933, abs=1e-4)


def test_recommend_stage_params_aligns_fall_with_target() -> None:
    stage = CurriculumStage(
        id="stand",
        name="Stand",
        order=0,
        timesteps=100_000,
        gaitTypeIds=["none"],
        termination=TerminationConfig(),
    )
    rec = recommend_stage_params(stage, rough=False)
    h = heights_for_target(rec.command.targetBodyHeight)
    assert rec.termination.fallBaseHeightThreshold == h.fall_base_height_threshold
    assert rec.termination.fallBaseHeightThreshold < rec.command.targetBodyHeight
