"""Curated quadruped RL training presets."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import (
    ParallelConfig,
    PpoHyperparams,
    RewardTerm,
    RlTrainerModel,
    TerminationConfig,
    VecEnvType,
)
from planner.defaults import SB3_BASELINE


@dataclass(frozen=True)
class PresetDefinition:
    id: str
    name: str
    description: str
    difficulty: str
    reward_terms: list[RewardTerm]
    termination: TerminationConfig
    hyperparams: PpoHyperparams
    parallel: ParallelConfig


def _term(
    tid: str,
    category: str,
    weight: float,
    term_type: str = "reward",
    **params: float,
) -> RewardTerm:
    return RewardTerm(
        id=tid,
        type=term_type,  # type: ignore[arg-type]
        category=category,
        weight=weight,
        enabled=True,
        params=dict(params),
    )


PRESET_CATALOG: list[PresetDefinition] = [
    PresetDefinition(
        id="velocity_tracking",
        name="Velocity tracking",
        description="Track commanded linear/angular velocity with orientation and torque penalties.",
        difficulty="beginner",
        reward_terms=[
            _term("lin_vel_tracking", "velocity", 1.0, target_lin_vel_x=1.0, sigma=0.25),
            _term("ang_vel_tracking", "velocity", 0.5, target_ang_vel_z=0.0, sigma=0.25),
            _term("orientation_penalty", "orientation", -0.5, sigma=0.1),
            _term("torque_penalty", "energy", -0.0002),
        ],
        termination=TerminationConfig(
            maxEpisodeSteps=1000,
            fallBaseHeightThreshold=0.15,
            maxTiltRad=0.8,
        ),
        hyperparams=SB3_BASELINE.model_copy(deep=True),
        parallel=ParallelConfig(numEnvs=1, vecEnvType=VecEnvType.SUBPROC),
    ),
    PresetDefinition(
        id="stand_still",
        name="Stand still",
        description="Balance in place with height/orientation rewards and low velocity penalty.",
        difficulty="beginner",
        reward_terms=[
            _term("base_height", "height", 1.0, target_height=0.35, sigma=0.05),
            _term("orientation_upright", "orientation", 0.8, sigma=0.1),
            _term("foot_contact", "contact", 0.3, min_contacts=2),
            _term("velocity_penalty", "velocity", -0.3, sigma=0.1),
        ],
        termination=TerminationConfig(
            maxEpisodeSteps=500,
            fallBaseHeightThreshold=0.12,
            maxTiltRad=0.6,
        ),
        hyperparams=SB3_BASELINE.model_copy(
            update={"totalTimesteps": 500_000, "entCoef": 0.01}
        ),
        parallel=ParallelConfig(numEnvs=1, vecEnvType=VecEnvType.DUMMY),
    ),
    PresetDefinition(
        id="efficient_locomotion",
        name="Efficient locomotion",
        description="Velocity tracking with stronger energy and impact penalties.",
        difficulty="intermediate",
        reward_terms=[
            _term("lin_vel_tracking", "velocity", 1.2, target_lin_vel_x=1.0, sigma=0.2),
            _term("ang_vel_tracking", "velocity", 0.6, target_ang_vel_z=0.0, sigma=0.2),
            _term("torque_penalty", "energy", -0.0005),
            _term("action_smoothness", "action_smoothness", -0.05, sigma=0.1),
            _term("impact_penalty", "contact", -0.1, max_impulse=50.0),
        ],
        termination=TerminationConfig(
            maxEpisodeSteps=1500,
            fallBaseHeightThreshold=0.14,
            maxTiltRad=0.75,
        ),
        hyperparams=SB3_BASELINE.model_copy(
            update={"nEpochs": 8, "entCoef": 0.005}
        ),
        parallel=ParallelConfig(numEnvs=2, vecEnvType=VecEnvType.SUBPROC),
    ),
    PresetDefinition(
        id="custom_blank",
        name="Custom (blank)",
        description="Empty reward list — configure manually or via custom params.",
        difficulty="advanced",
        reward_terms=[],
        termination=TerminationConfig(),
        hyperparams=SB3_BASELINE.model_copy(deep=True),
        parallel=ParallelConfig(numEnvs=1, vecEnvType=VecEnvType.DUMMY),
    ),
]


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
    model.termination = preset.termination.model_copy(deep=True)
    model.hyperparams = preset.hyperparams.model_copy(deep=True)
    model.parallel = preset.parallel.model_copy(deep=True)
    return model
