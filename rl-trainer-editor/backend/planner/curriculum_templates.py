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
from planner.gait_defaults import resolve_gait_id
from planner.recommender import recommend_stage_params
from planner.standing_heights import PLACEHOLDER_BODY_HEIGHT_M, heights_for_target
from planner.reward_catalog import locomotion_reward_terms, stand_reward_terms

# (stage_id, gait_type_id, name, description, timesteps, target_lin_vel_x)
_STAGE_DEFS = [
    ("stand", "none", "Stand", "Learn stable balance before any commanded motion.", 400_000, 0.0),
    ("recover", "none", "Recover", "Recover posture after perturbations.", 400_000, 0.0),
    ("walk", "walk", "Walk", "Comfortable walking with velocity tracking.", 550_000, 0.5),
    ("trot", "trot", "Trot", "Diagonal gait at moderate speed.", 600_000, 0.8),
    ("pace", "pace", "Pace / Lateral trot", "Lateral pair gait.", 600_000, 1.0),
    ("bound", "bound", "Bound", "Front/rear pair bounding.", 650_000, 1.2),
    ("gallop", "gallop", "Gallop", "High speed gallop — final stage.", 700_000, 1.4),
]


def _stand_terms() -> list[RewardTerm]:
    return stand_reward_terms()


def _locomotion_terms(lin_x: float, ang_z: float = 0.0) -> list[RewardTerm]:
    return locomotion_reward_terms(lin_x, ang_z)


def _build_stage(
    order: int,
    stage_id: str,
    gait_type_id: str,
    name: str,
    description: str,
    timesteps: int,
    lin_vel: float,
    rough: bool,
) -> CurriculumStage:
    is_stand = lin_vel == 0.0 and resolve_gait_id(gait_type_id) == "none"
    rewards = _stand_terms() if is_stand else _locomotion_terms(lin_vel)
    cmd = StageCommand(
        targetLinVelX=lin_vel,
        targetLinVelY=0.0,
        targetAngVelZ=0.0,
        targetBodyHeight=PLACEHOLDER_BODY_HEIGHT_M,
        gaitSpeedScale=1.0 + order * 0.08,
    )
    stage = CurriculumStage(
        id=stage_id,
        name=name,
        order=order,
        description=description,
        timesteps=timesteps,
        targetLinVelX=lin_vel,
        targetAngVelZ=0.0,
        gaitTypeIds=[gait_type_id],
        command=cmd,
        disturbance=DisturbanceConfig(),  # placeholder; recommend_stage_params sets the live value
        rewardTerms=rewards,
        termination=TerminationConfig(
            maxEpisodeSteps=800 + order * 200,
            fallBaseHeightThreshold=heights_for_target(PLACEHOLDER_BODY_HEIGHT_M).fall_base_height_threshold,
            # Kept in sync with recommend_stage_params (recommender.py), which
            # overwrites this block via _build_stage; same formula avoids drift.
            maxTiltRad=min(1.2, 0.75 + order * 0.06),
        ),
        advanceCriteria=CurriculumAdvanceCriteria(
            minMeanEpisodeReward=max(0.25, 0.65 - order * 0.06),
            minEpisodeLengthFrac=max(0.65, 0.90 - order * 0.04),
            maxFallRate=min(0.20, 0.08 + order * 0.02),
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
        _build_stage(i, sid, gid, name, desc, ts, vel, rough)
        for i, (sid, gid, name, desc, ts, vel) in enumerate(_STAGE_DEFS)
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
        "description": "Seven stages from balance through gallop on flat terrain.",
        "stageCount": 7,
        "totalTimesteps": sum(d[4] for d in _STAGE_DEFS),
        "terrainProfile": "flat",
    },
    {
        "id": "stand_sprint_rough",
        "name": "Stand → Sprint (rough terrain)",
        "description": "Same seven-stage progression with disturbances and rough terrain.",
        "stageCount": 7,
        "totalTimesteps": int(sum(d[4] for d in _STAGE_DEFS) * 1.1),
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
