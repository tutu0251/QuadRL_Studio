"""Curated quadruped RL training presets."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import RewardTerm, RlTrainerModel, TerminationConfig
from domain.models import StageCommand
from planner.reward_catalog import (
    build_full_reward_catalog,
    locomotion_reward_terms,
    recommend_term_params,
    stand_reward_terms,
)
from planner.termination_catalog import build_full_termination_catalog, merge_termination_config


@dataclass(frozen=True)
class PresetDefinition:
    id: str
    name: str
    description: str
    difficulty: str
    reward_terms: list[RewardTerm]
    termination: TerminationConfig


def _velocity_tracking_terms() -> list[RewardTerm]:
    cmd = StageCommand(targetLinVelX=1.0, targetBodyHeight=0.35)
    terms = build_full_reward_catalog()
    enabled = {
        "forward_tracking",
        "yaw_tracking",
        "upright",
        "posture_penalty",
        "joint_velocity",
        "action_rate",
    }
    out: list[RewardTerm] = []
    for t in terms:
        term = t.model_copy(deep=True)
        term.enabled = t.id in enabled
        if term.enabled:
            term = recommend_term_params(term, cmd, lin_vel_scale=1.0)
        out.append(term)
    return out


def _efficient_locomotion_terms() -> list[RewardTerm]:
    cmd = StageCommand(targetLinVelX=1.0, targetBodyHeight=0.35, gaitSpeedScale=1.1)
    terms = locomotion_reward_terms(1.0, cmd=cmd)
    extra_on = {"stumble", "slip", "smoothness", "zmp", "contact_balance"}
    for i, t in enumerate(terms):
        if t.id in extra_on:
            terms[i] = t.model_copy(update={"enabled": True})
    return terms


PRESET_CATALOG: list[PresetDefinition] = [
    PresetDefinition(
        id="velocity_tracking",
        name="Velocity tracking",
        description="Track commanded velocity with posture and energy penalties.",
        difficulty="beginner",
        reward_terms=_velocity_tracking_terms(),
        termination=TerminationConfig(
            maxEpisodeSteps=1000,
            fallBaseHeightThreshold=0.15,
            maxTiltRad=0.8,
        ),
    ),
    PresetDefinition(
        id="stand_still",
        name="Stand still",
        description="Balance in place with survival, height, and velocity penalties.",
        difficulty="beginner",
        reward_terms=stand_reward_terms(),
        termination=TerminationConfig(
            maxEpisodeSteps=500,
            fallBaseHeightThreshold=0.12,
            maxTiltRad=0.6,
        ),
    ),
    PresetDefinition(
        id="efficient_locomotion",
        name="Efficient locomotion",
        description="Full locomotion rewards with stronger energy, slip, and ZMP penalties.",
        difficulty="intermediate",
        reward_terms=_efficient_locomotion_terms(),
        termination=TerminationConfig(
            maxEpisodeSteps=1500,
            fallBaseHeightThreshold=0.14,
            maxTiltRad=0.75,
        ),
    ),
    PresetDefinition(
        id="custom_blank",
        name="Custom (blank)",
        description="Full reward/penalty catalog — enable terms manually.",
        difficulty="advanced",
        reward_terms=build_full_reward_catalog(),
        termination=TerminationConfig(
            terminationTerms=build_full_termination_catalog(),
        ),
    ),
]


def _termination_with_catalog(base: TerminationConfig) -> TerminationConfig:
    t = merge_termination_config(base)
    return t


def list_presets() -> list[dict]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "difficulty": p.difficulty,
        }
        for p in PRESET_CATALOG
    ]


def get_preset(preset_id: str) -> PresetDefinition:
    for p in PRESET_CATALOG:
        if p.id == preset_id:
            return p
    raise KeyError(f"Unknown preset: {preset_id}")


def apply_preset_to_model(model: RlTrainerModel, preset_id: str) -> RlTrainerModel:
    preset = get_preset(preset_id)
    model.selectedPresetId = preset_id
    model.rewardTerms = [t.model_copy(deep=True) for t in preset.reward_terms]
    model.termination = _termination_with_catalog(preset.termination)
    return model
