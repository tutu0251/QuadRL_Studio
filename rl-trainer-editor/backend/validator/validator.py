"""Validate RL trainer config before export."""
from __future__ import annotations

import math

from domain.models import RlTrainerModel, ValidationIssue, ValidationResult
from storage import project_storage


_CATEGORY_OBS: dict[str, set[str]] = {
    "contact": {"contact"},
    "velocity": set(),
    "orientation": {"imu"},
    "energy": set(),
    "height": set(),
    "action_smoothness": set(),
}


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

        if cur.enabled:
            if len(cur.stages) < 2:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="curriculum_min_stages",
                        message="Progressive curriculum needs at least 2 stages.",
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
            if cur.currentStageIndex >= len(cur.stages):
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="curriculum_stage_index",
                        message="currentStageIndex is past the last stage.",
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
