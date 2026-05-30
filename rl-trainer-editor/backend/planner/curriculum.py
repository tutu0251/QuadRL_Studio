"""Progressive training curricula — stand still through sprint."""
from __future__ import annotations

from domain.models import (
    CurriculumAdvanceCriteria,
    CurriculumConfig,
    CurriculumStage,
    RewardTerm,
    RlTrainerModel,
    TerminationConfig,
)


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


def _stand_still_terms() -> list[RewardTerm]:
    return [
        _term("base_height", "height", 1.0, target_height=0.35, sigma=0.05),
        _term("orientation_upright", "orientation", 0.8, sigma=0.1),
        _term("foot_contact", "contact", 0.3, min_contacts=2),
        _term("velocity_penalty", "velocity", -0.4, sigma=0.08),
    ]


def _locomotion_terms(target_lin_vel_x: float, target_ang_vel_z: float = 0.0) -> list[RewardTerm]:
    return [
        _term(
            "lin_vel_tracking",
            "velocity",
            1.0,
            target_lin_vel_x=target_lin_vel_x,
            sigma=0.2,
        ),
        _term(
            "ang_vel_tracking",
            "velocity",
            0.5,
            target_ang_vel_z=target_ang_vel_z,
            sigma=0.2,
        ),
        _term("orientation_penalty", "orientation", -0.4, sigma=0.1),
        _term("torque_penalty", "energy", -0.0002),
        _term("base_height", "height", 0.3, target_height=0.35, sigma=0.08),
    ]


def build_stand_to_sprint_curriculum() -> CurriculumConfig:
    """Step-by-step: stand → walk → jog → run → sprint."""
    stages = [
        CurriculumStage(
            id="stand_still",
            name="Stand still",
            order=0,
            description="Learn stable balance before any commanded motion.",
            timesteps=300_000,
            targetLinVelX=0.0,
            targetAngVelZ=0.0,
            rewardTerms=_stand_still_terms(),
            termination=TerminationConfig(
                maxEpisodeSteps=500,
                fallBaseHeightThreshold=0.12,
                maxTiltRad=0.55,
            ),
            advanceCriteria=CurriculumAdvanceCriteria(
                minMeanEpisodeReward=0.5,
                minEpisodeLengthFrac=0.85,
                maxFallRate=0.15,
            ),
        ),
        CurriculumStage(
            id="slow_walk",
            name="Slow walk",
            order=1,
            description="Introduce low forward velocity while keeping posture.",
            timesteps=400_000,
            targetLinVelX=0.3,
            targetAngVelZ=0.0,
            rewardTerms=_locomotion_terms(0.3),
            termination=TerminationConfig(maxEpisodeSteps=800, maxTiltRad=0.65),
            advanceCriteria=CurriculumAdvanceCriteria(
                minMeanEpisodeReward=0.4,
                minEpisodeLengthFrac=0.75,
                maxFallRate=0.2,
            ),
        ),
        CurriculumStage(
            id="walk",
            name="Walk",
            order=2,
            description="Comfortable walking speed with velocity tracking.",
            timesteps=400_000,
            targetLinVelX=0.6,
            rewardTerms=_locomotion_terms(0.6),
            termination=TerminationConfig(maxEpisodeSteps=1000, maxTiltRad=0.7),
            advanceCriteria=CurriculumAdvanceCriteria(
                minMeanEpisodeReward=0.35,
                minEpisodeLengthFrac=0.7,
                maxFallRate=0.22,
            ),
        ),
        CurriculumStage(
            id="run",
            name="Run",
            order=3,
            description="Faster locomotion — higher velocity target and longer episodes.",
            timesteps=500_000,
            targetLinVelX=1.0,
            rewardTerms=_locomotion_terms(1.0),
            termination=TerminationConfig(maxEpisodeSteps=1200, maxTiltRad=0.75),
            advanceCriteria=CurriculumAdvanceCriteria(
                minMeanEpisodeReward=0.3,
                minEpisodeLengthFrac=0.65,
                maxFallRate=0.25,
            ),
        ),
        CurriculumStage(
            id="sprint",
            name="Sprint",
            order=4,
            description="Maximum training velocity — final curriculum stage.",
            timesteps=500_000,
            targetLinVelX=1.5,
            rewardTerms=_locomotion_terms(1.5),
            termination=TerminationConfig(maxEpisodeSteps=1500, maxTiltRad=0.8),
            advanceCriteria=CurriculumAdvanceCriteria(
                minMeanEpisodeReward=0.25,
                minEpisodeLengthFrac=0.6,
                maxFallRate=0.3,
            ),
        ),
    ]
    return CurriculumConfig(
        enabled=True,
        curriculumId="stand_to_sprint",
        name="Stand still → Sprint",
        description="Progressive curriculum: balance, then walk, run, and sprint.",
        stages=stages,
        loadPreviousCheckpoint=True,
        resetPolicyOnStageAdvance=False,
    )


CURRICULUM_CATALOG: list[dict] = [
    {
        "id": "stand_to_sprint",
        "name": "Stand still → Sprint",
        "description": "Five stages from balance to sprint (2.1M total steps).",
        "stageCount": 5,
        "totalTimesteps": 2_100_000,
    },
]


def list_curricula() -> list[dict]:
    return list(CURRICULUM_CATALOG)


def get_curriculum_template(curriculum_id: str) -> CurriculumConfig:
    if curriculum_id == "stand_to_sprint":
        return build_stand_to_sprint_curriculum()
    raise KeyError(f"Unknown curriculum: {curriculum_id}")


def curriculum_total_timesteps(config: CurriculumConfig) -> int:
    if not config.enabled or not config.stages:
        return 0
    return sum(s.timesteps for s in config.stages)


def apply_curriculum_first_stage(model: RlTrainerModel, config: CurriculumConfig) -> None:
    """Set active task fields from the first curriculum stage."""
    if not config.stages:
        return
    first = sorted(config.stages, key=lambda s: s.order)[0]
    model.rewardTerms = [t.model_copy(deep=True) for t in first.rewardTerms]
    model.termination = first.termination.model_copy(deep=True)
    model.selectedPresetId = f"curriculum:{config.curriculumId}"
