"""Validate RL trainer config before export."""
from __future__ import annotations

import math
from pathlib import Path

from domain.models import RlTrainerModel, ValidationIssue, ValidationResult
from domain.stage_gait import stage_gait_type_ids, stage_is_stand_only
from storage import project_storage


_CATEGORY_OBS: dict[str, set[str]] = {
    "contact": {"contact"},
    "velocity": set(),
    "orientation": {"imu"},
    "energy": set(),
    "height": set(),
    "action_smoothness": set(),
    "posture": {"imu"},
    "gait": {"contact"},
    "survival": set(),
    "tracking": set(),
    "stability": set(),
}

_GAIT_IDS = {"none", "walk", "trot", "gallop"}


class RlTrainerValidator:
    def __init__(self, model: RlTrainerModel):
        self._model = model

    def validate(self) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        project = self._model.projectName
        cur = self._model.curriculum
        enabled_terms = [t for t in self._model.rewardTerms if t.enabled]
        has_curriculum = cur.enabled and len(cur.stages) >= 2

        if not has_curriculum and not enabled_terms and not self._model.customParams:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="no_task_definition",
                    message="Enable at least one reward term, a curriculum, or custom_params.",
                )
            )

        gait_ids = {g.id for g in self._model.gaitTypes}

        for gait in self._model.gaitTypes:
            if gait.dutyFactor <= 0 or gait.dutyFactor > 1:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_duty_factor",
                        message=f"Gait '{gait.id}' dutyFactor must be in (0, 1].",
                    )
                )
            for leg, val in gait.phaseOffsets.model_dump().items():
                if val < 0 or val >= 1:
                    warnings.append(
                        ValidationIssue(
                            severity="warning",
                            code="phase_offset_range",
                            message=f"Gait '{gait.id}' phase offset {leg}={val} outside [0, 1).",
                        )
                    )

        if cur.enabled:
            if len(cur.stages) < 2:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="curriculum_min_stages",
                        message="Progressive curriculum needs at least 2 stages.",
                    )
                )
            if not cur.name.strip():
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="empty_curriculum_name",
                        message="Curriculum name cannot be empty.",
                    )
                )
            orders = [s.order for s in cur.stages]
            if len(orders) != len(set(orders)):
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="duplicate_stage_order",
                        message="Curriculum stages have duplicate order values.",
                    )
                )
            for stage in cur.stages:
                if stage.timesteps < 10_000:
                    warnings.append(
                        ValidationIssue(
                            severity="warning",
                            code="low_stage_timesteps",
                            message=f"Stage '{stage.id}' has fewer than 10k timesteps.",
                        )
                    )
                if not stage.rewardTerms:
                    errors.append(
                        ValidationIssue(
                            severity="error",
                            code="empty_stage_rewards",
                            message=f"Stage '{stage.id}' has no reward terms.",
                        )
                    )
                stage_gaits = stage_gait_type_ids(stage)
                if not stage_gaits:
                    errors.append(
                        ValidationIssue(
                            severity="error",
                            code="missing_gait_type",
                            message=f"Stage '{stage.id}' has no gate types selected.",
                        )
                    )
                for resolved_gait in stage_gaits:
                    if resolved_gait not in gait_ids:
                        errors.append(
                            ValidationIssue(
                                severity="error",
                                code="missing_gait_type",
                                message=f"Stage '{stage.id}' references unknown gate type '{resolved_gait}'.",
                            )
                        )
                if (
                    cur.terrainProfile == "rough"
                    and not stage.disturbance.enabled
                    and not stage_is_stand_only(stage)
                ):
                    warnings.append(
                        ValidationIssue(
                            severity="warning",
                            code="rough_no_disturbance",
                            message=f"Stage '{stage.id}' on rough terrain has disturbances disabled.",
                        )
                    )
            if cur.currentStageIndex >= len(cur.stages):
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="curriculum_stage_index",
                        message="currentStageIndex is past the last stage.",
                    )
                )

        tc = self._model.trainingCheckpoint
        if tc.resumeCheckpointPath:
            if project:
                ckpt_path = project_storage.project_dir(project) / tc.resumeCheckpointPath
                if not ckpt_path.is_file():
                    warnings.append(
                        ValidationIssue(
                            severity="warning",
                            code="missing_resume_checkpoint",
                            message=f"Resume checkpoint not found: {tc.resumeCheckpointPath}",
                        )
                    )
            if cur.resetPolicyOnStageAdvance:
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="resume_reset_conflict",
                        message="Resume checkpoint selected while resetPolicyOnStageAdvance is enabled.",
                    )
                )

        for term in self._model.rewardTerms:
            if not term.enabled:
                continue
            if not math.isfinite(term.weight):
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_weight",
                        message=f"Term '{term.id}' has non-finite weight.",
                    )
                )
            if term.category == "velocity" and term.type == "reward":
                if not any(k.startswith("target_") for k in term.params):
                    warnings.append(
                        ValidationIssue(
                            severity="warning",
                            code="velocity_targets",
                            message=f"Term '{term.id}' has no target_* velocity params.",
                        )
                    )

        t = self._model.termination
        if t.maxEpisodeSteps < 1:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="max_episode_steps",
                    message="maxEpisodeSteps must be at least 1.",
                )
            )
        if t.fallBaseHeightThreshold <= 0:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="fall_height",
                    message="fallBaseHeightThreshold must be positive.",
                )
            )
        if t.maxTiltRad <= 0 or t.maxTiltRad > math.pi:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="max_tilt",
                    message="maxTiltRad must be in (0, π].",
                )
            )

        if project:
            if not project_storage.export_ppo_yaml_path(project).exists():
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="missing_ppo_config",
                        message=(
                            "ppo_*_config.yaml not found — export from PPO Planner for "
                            "hyperparameters and parallel env settings."
                        ),
                    )
                )
            if not project_storage.observations_yaml_path(project).exists():
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="missing_observations",
                        message="sens_*_observations.yaml not found — export from sensor editor first.",
                    )
                )
            if not project_storage.gains_yaml_path(project).exists():
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="missing_gains",
                        message="ctrl_*_gains.yaml not found — export from control editor first.",
                    )
                )
            kinds = project_storage.load_observation_kinds(project)
            selected_kinds = {
                str(t.kind).lower()
                for t in self._model.observationTerms
                if t.enabled and t.available
            }
            if selected_kinds:
                kinds = selected_kinds
            if self._model.observationTerms and not any(
                t.enabled and t.available for t in self._model.observationTerms
            ):
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="no_observations_selected",
                        message="No observations enabled — enable terms in the Observations tab.",
                    )
                )
            for term in enabled_terms:
                required = _CATEGORY_OBS.get(term.category)
                if required and kinds and not (required & kinds):
                    warnings.append(
                        ValidationIssue(
                            severity="warning",
                            code="obs_mismatch",
                            message=(
                                f"Reward term '{term.id}' (category={term.category}) may need "
                                f"observation kinds {sorted(required)}; found {sorted(kinds)}."
                            ),
                        )
                    )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
