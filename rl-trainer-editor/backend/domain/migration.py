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
from planner.observation_normalization import apply_recommended_normalization
from planner.observation_recommender import sync_observations
from planner.reward_catalog import merge_reward_terms
from planner.standing_heights import (
    PLACEHOLDER_BODY_HEIGHT_M,
    StandingHeightParams,
    assert_height_policy_consistent,
    fall_threshold_for_target,
    heights_for_target,
)
from planner.termination_catalog import merge_termination_config
from storage import project_storage
from storage.project_storage import EXPORTS_DIR


def _load_project_heights(project_name: str) -> StandingHeightParams | None:
    """Grounded heights from geo default-pose export when available."""
    if not project_name:
        return None
    exports = project_storage.project_dir(project_name) / EXPORTS_DIR
    pose_path = exports / f"geo_{project_name}_default_pose.yaml"
    if not pose_path.is_file():
        return None
    try:
        import yaml

        doc = yaml.safe_load(pose_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    policy = doc.get("height_policy") or {}
    if policy.get("target_body_height") is not None and policy.get("fall_base_height_threshold") is not None:
        params = StandingHeightParams(
            spawn_z=float(policy.get("spawn_z", policy["target_body_height"])),
            target_body_height=float(policy["target_body_height"]),
            fall_base_height_threshold=float(policy["fall_base_height_threshold"]),
            fall_drop_margin_m=float(policy.get("fall_drop_margin_m", 0.10)),
        )
        try:
            assert_height_policy_consistent(params)
        except ValueError:
            return None
        return params
    return None


def _apply_heights_to_stage(stage: CurriculumStage, heights: StandingHeightParams) -> None:
    stage.command.targetBodyHeight = heights.target_body_height
    stage.termination.fallBaseHeightThreshold = heights.fall_base_height_threshold
    for term in stage.rewardTerms:
        if term.id == "height":
            term.params["target_height"] = heights.target_body_height


def _align_stage_heights(stage: CurriculumStage, project_heights: StandingHeightParams | None) -> CurriculumStage:
    s = stage.model_copy(deep=True)
    if project_heights is not None:
        _apply_heights_to_stage(s, project_heights)
        return s
    target = float(s.command.targetBodyHeight or PLACEHOLDER_BODY_HEIGHT_M)
    heights = heights_for_target(target)
    expected_fall = fall_threshold_for_target(target)
    if s.termination.fallBaseHeightThreshold != expected_fall:
        _apply_heights_to_stage(s, heights)
    else:
        for term in s.rewardTerms:
            if term.id == "height" and term.params.get("target_height") != target:
                term.params["target_height"] = target
    return s


def _migrate_stage(stage: CurriculumStage, project_heights: StandingHeightParams | None = None) -> CurriculumStage:
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
            targetBodyHeight=PLACEHOLDER_BODY_HEIGHT_M,
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
    s.termination = merge_termination_config(s.termination)
    return _align_stage_heights(s, project_heights)


_CATALOG_IDS = frozenset({"none", "walk", "trot", "gallop"})


def migrate_model(model: RlTrainerModel) -> RlTrainerModel:
    library_ids = {g.id for g in model.gaitTypes}
    if not model.gaitTypes or not library_ids.issubset(_CATALOG_IDS) or len(model.gaitTypes) != 4:
        model.gaitTypes = default_gait_library()

    if not model.trainingCheckpoint:
        model.trainingCheckpoint = TrainingCheckpointConfig()

    project_heights = _load_project_heights(model.projectName)

    cur = model.curriculum
    if not getattr(cur, "terrainProfile", None):
        cur.terrainProfile = "flat"
    cur.stages = [_migrate_stage(s, project_heights) for s in cur.stages]

    if not model.curriculumLibrary:
        entry = curriculum_to_entry(cur)
        if not entry.id:
            entry.id = cur.curriculumId or new_id()
        model.curriculumLibrary = [entry]
        model.activeCurriculumId = entry.id
    else:
        for entry in model.curriculumLibrary:
            entry.stages = [_migrate_stage(s, project_heights) for s in entry.stages]

    if not model.activeCurriculumId and model.curriculumLibrary:
        model.activeCurriculumId = model.curriculumLibrary[0].id

    model.rewardTerms = merge_reward_terms(model.rewardTerms)
    model.termination = merge_termination_config(model.termination)
    if project_heights is not None:
        model.termination.fallBaseHeightThreshold = project_heights.fall_base_height_threshold
        for term in model.rewardTerms:
            if term.id == "height":
                term.params["target_height"] = project_heights.target_body_height
    else:
        target = PLACEHOLDER_BODY_HEIGHT_M
        expected_fall = fall_threshold_for_target(target)
        if model.termination.fallBaseHeightThreshold != expected_fall:
            model.termination.fallBaseHeightThreshold = expected_fall
            for term in model.rewardTerms:
                if term.id == "height":
                    term.params["target_height"] = target
    sync_observations(model)
    if model.observationTerms:
        for term in model.observationTerms:
            if term.source == "sensor" and not term.availableFields:
                term.availableFields = list(term.fields)
            apply_recommended_normalization(term)
    model.version = "2.5"
    return model
