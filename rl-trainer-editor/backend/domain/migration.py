"""Migrate legacy RL trainer models to v2 schema."""
from __future__ import annotations

from domain.models import (
    CurriculumConfig,
    CurriculumEntry,
    CurriculumStage,
    DisturbanceConfig,
    RlTrainerModel,
    StageCommand,
    TrainingCheckpointConfig,
    new_id,
)
from planner.curriculum_templates import curriculum_to_entry
from domain.stage_gait import stage_gait_type_ids
from planner.gait_defaults import default_gait_library
from planner.reward_catalog import merge_reward_terms


def _migrate_stage(stage: CurriculumStage) -> CurriculumStage:
    s = stage.model_copy(deep=True)
    if not s.command or (
        s.command.targetLinVelX == 0
        and s.command.targetLinVelY == 0
        and s.command.gaitSpeedScale == 1.0
        and s.targetLinVelX != 0
    ):
        s.command = StageCommand(
            targetLinVelX=s.targetLinVelX,
            targetLinVelY=0.0,
            targetAngVelZ=s.targetAngVelZ,
            targetBodyHeight=0.35,
            gaitSpeedScale=1.0,
        )
    else:
        s.targetLinVelX = s.command.targetLinVelX
        s.targetAngVelZ = s.command.targetAngVelZ
    if not s.gaitTypeIds:
        s.gaitTypeIds = ["walk"] if s.targetLinVelX > 0 else ["none"]
    s.gaitTypeIds = stage_gait_type_ids(s)
    if s.disturbance is None:
        s.disturbance = DisturbanceConfig()
    s.rewardTerms = merge_reward_terms(s.rewardTerms)
    return s


_CATALOG_IDS = frozenset({"none", "walk", "trot", "gallop"})


def migrate_model(model: RlTrainerModel) -> RlTrainerModel:
    library_ids = {g.id for g in model.gaitTypes}
    if not model.gaitTypes or not library_ids.issubset(_CATALOG_IDS) or len(model.gaitTypes) != 4:
        model.gaitTypes = default_gait_library()

    if not model.trainingCheckpoint:
        model.trainingCheckpoint = TrainingCheckpointConfig()

    cur = model.curriculum
    if not getattr(cur, "terrainProfile", None):
        cur.terrainProfile = "flat"
    cur.stages = [_migrate_stage(s) for s in cur.stages]

    if not model.curriculumLibrary:
        entry = curriculum_to_entry(cur)
        if not entry.id:
            entry.id = cur.curriculumId or new_id()
        model.curriculumLibrary = [entry]
        model.activeCurriculumId = entry.id
    else:
        for entry in model.curriculumLibrary:
            entry.stages = [_migrate_stage(s) for s in entry.stages]

    if not model.activeCurriculumId and model.curriculumLibrary:
        model.activeCurriculumId = model.curriculumLibrary[0].id

    model.rewardTerms = merge_reward_terms(model.rewardTerms)
    model.version = "2.1"
    return model
