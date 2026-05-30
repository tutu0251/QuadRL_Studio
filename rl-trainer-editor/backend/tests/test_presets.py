"""Tests for RL training presets."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import RlTrainerModel
from planner.presets import PRESET_CATALOG, apply_preset_to_model, get_preset


def test_all_presets_apply():
    for preset in PRESET_CATALOG:
        model = RlTrainerModel(projectName="test", robotName="test")
        apply_preset_to_model(model, preset.id)
        assert model.selectedPresetId == preset.id
        if preset.id != "custom_blank":
            assert len(model.rewardTerms) > 0


def test_velocity_tracking_has_velocity_terms():
    preset = get_preset("velocity_tracking")
    categories = {t.category for t in preset.reward_terms}
    assert "velocity" in categories
