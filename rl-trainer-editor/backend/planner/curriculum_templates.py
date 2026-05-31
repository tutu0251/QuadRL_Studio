"""Gait-based progressive training curricula."""
from __future__ import annotations

from domain.models import (
    CurriculumAdvanceCriteria,
    CurriculumConfig,
    CurriculumEntry,
    CurriculumStage,
    DisturbanceConfig,
    RewardTerm,
    StageCommand,
    TerminationConfig,
    new_id,
)
from planner.recommender import recommend_stage_params
from planner.reward_catalog import locomotion_reward_terms, stand_reward_terms

_STAGE_DEFS = [
    ("none", "None", "Learn stable balance before any commanded motion.", 400_000, 0.0),
    ("walk", "Walk", "Comfortable walking with velocity tracking.", 500_000, 0.4),
    ("trot", "Trot", "Diagonal gate type at moderate speed.", 550_000, 0.8),
    ("gallop", "Gallop", "Maximum speed gallop — final stage.", 650_000, 1.5),
]


def _stand_terms() -> list[RewardTerm]:
    return stand_reward_terms()


def _locomotion_terms(lin_x: float, ang_z: float = 0.0) -> list[RewardTerm]:
    return locomotion_reward_terms(lin_x, ang_z)


def _disturbance_for_gait(gait_id: str, rough: bool) -> DisturbanceConfig:
    if not rough:
        return DisturbanceConfig()
    scale = {
        "none": 0.15,
        "walk": 0.35,
        "trot": 0.55,
        "gallop": 0.75,
    }.get(gait_id, 0.3)
    return DisturbanceConfig(
        enabled=True,
        pushForceN=15 + scale * 30,
        pushIntervalSteps=max(300, int(800 - scale * 400)),
        terrainRoughness=scale,
        lateralImpulseN=5 + scale * 15,
        randomOrientationNoiseRad=0.02 + scale * 0.06,
    )


def _build_stage(
    order: int,
    gait_id: str,
    name: str,
    description: str,
    timesteps: int,
    lin_vel: float,
    rough: bool,
) -> CurriculumStage:
    rewards = _stand_terms() if lin_vel == 0.0 and gait_id == "none" else _locomotion_terms(lin_vel)
    cmd = StageCommand(
        targetLinVelX=lin_vel,
        targetLinVelY=0.0,
        targetAngVelZ=0.0,
        targetBodyHeight=0.35,
        gaitSpeedScale=1.0 + order * 0.05,
    )
    stage = CurriculumStage(
        id=gait_id,
        name=name,
        order=order,
        description=description,
        timesteps=timesteps,
        targetLinVelX=lin_vel,
        targetAngVelZ=0.0,
        gaitTypeIds=[gait_id],
        command=cmd,
        disturbance=_disturbance_for_gait(gait_id, rough),
        rewardTerms=rewards,
        termination=TerminationConfig(
            maxEpisodeSteps=500 + order * 150,
            fallBaseHeightThreshold=0.12,
            maxTiltRad=0.55 + order * 0.04,
        ),
        advanceCriteria=CurriculumAdvanceCriteria(
            minMeanEpisodeReward=max(0.2, 0.55 - order * 0.05),
            minEpisodeLengthFrac=max(0.55, 0.85 - order * 0.04),
            maxFallRate=min(0.35, 0.15 + order * 0.03),
        ),
    )
    recommended = recommend_stage_params(stage, rough)
    stage.command = recommended.command
    stage.disturbance = recommended.disturbance
    stage.timesteps = recommended.timesteps
    stage.termination = recommended.termination
    stage.advanceCriteria = recommended.advanceCriteria
    stage.rewardTerms = recommended.rewardTerms
    stage.paramEnabled = recommended.paramEnabled
    return stage


def build_stand_sprint_curriculum(rough: bool = False) -> CurriculumConfig:
    terrain = "rough" if rough else "flat"
    cid = "stand_sprint_rough" if rough else "stand_sprint"
    cname = "Stand → Sprint (rough terrain)" if rough else "Stand → Sprint (flat)"
    stages = [
        _build_stage(i, gid, name, desc, ts, vel, rough)
        for i, (gid, name, desc, ts, vel) in enumerate(_STAGE_DEFS)
    ]
    for i, s in enumerate(stages):
        s.id = _STAGE_DEFS[i][0]
        s.order = i
    return CurriculumConfig(
        enabled=True,
        curriculumId=cid,
        name=cname,
        description=f"Progressive gait curriculum on {terrain} terrain.",
        terrainProfile=terrain,  # type: ignore[arg-type]
        stages=stages,
        loadPreviousCheckpoint=True,
        resetPolicyOnStageAdvance=False,
    )


def curriculum_to_entry(config: CurriculumConfig) -> CurriculumEntry:
    return CurriculumEntry(
        id=config.curriculumId or new_id(),
        name=config.name,
        description=config.description,
        terrainProfile=config.terrainProfile,
        stages=[s.model_copy(deep=True) for s in config.stages],
        loadPreviousCheckpoint=config.loadPreviousCheckpoint,
        resetPolicyOnStageAdvance=config.resetPolicyOnStageAdvance,
    )


CURRICULUM_CATALOG: list[dict] = [
    {
        "id": "stand_sprint",
        "name": "Stand → Sprint (flat)",
        "description": "Four gate types from none through gallop on flat terrain.",
        "stageCount": 4,
        "totalTimesteps": sum(d[3] for d in _STAGE_DEFS),
        "terrainProfile": "flat",
    },
    {
        "id": "stand_sprint_rough",
        "name": "Stand → Sprint (rough terrain)",
        "description": "Same gate-type progression with disturbances and rough terrain.",
        "stageCount": 4,
        "totalTimesteps": int(sum(d[3] for d in _STAGE_DEFS) * 1.1),
        "terrainProfile": "rough",
    },
]


def list_curricula() -> list[dict]:
    return list(CURRICULUM_CATALOG)


def get_curriculum_template(curriculum_id: str) -> CurriculumConfig:
    if curriculum_id == "stand_sprint":
        return build_stand_sprint_curriculum(rough=False)
    if curriculum_id == "stand_sprint_rough":
        return build_stand_sprint_curriculum(rough=True)
    if curriculum_id == "stand_to_sprint":
        return build_stand_sprint_curriculum(rough=False)
    raise KeyError(f"Unknown curriculum: {curriculum_id}")


def curriculum_total_timesteps(config: CurriculumConfig) -> int:
    if not config.enabled or not config.stages:
        return 0
    return sum(s.timesteps for s in config.stages)


def apply_curriculum_first_stage(model, config: CurriculumConfig) -> None:
    if not config.stages:
        return
    first = sorted(config.stages, key=lambda s: s.order)[0]
    model.rewardTerms = [t.model_copy(deep=True) for t in first.rewardTerms]
    model.termination = first.termination.model_copy(deep=True)
    model.selectedPresetId = f"curriculum:{config.curriculumId}"
