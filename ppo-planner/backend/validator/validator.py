"""Validate PPO hyperparameters before export."""
from __future__ import annotations

from domain.models import PpoPlannerModel, ValidationIssue, ValidationResult
from exporter.format_registry import JSON_LIKE
from planner.parallel_guard import parallel_validation_issues
from profiler.machine_profiler import profile_machine


class PpoValidator:
    def __init__(self, model: PpoPlannerModel):
        self._model = model

    def validate(self) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        p = self._model.params
        par = self._model.parallel

        if p.learningRate <= 0 or p.learningRate > 1:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="learning_rate_range",
                    message="learning_rate must be in (0, 1].",
                )
            )
        if p.nSteps < 64:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="n_steps_min",
                    message="n_steps should be at least 64.",
                )
            )
        if p.batchSize < 8:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="batch_size_min",
                    message="batch_size should be at least 8.",
                )
            )
        if not 0 < p.gamma <= 1:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="gamma_range",
                    message="gamma must be in (0, 1].",
                )
            )
        if not 0 <= p.gaeLambda <= 1:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="gae_lambda_range",
                    message="gae_lambda must be in [0, 1].",
                )
            )
        if p.clipRange <= 0 or p.clipRange > 1:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="clip_range",
                    message="clip_range must be in (0, 1].",
                )
            )
        if p.totalTimesteps < 10_000:
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="low_timesteps",
                    message="total_timesteps below 10k may not train a useful policy.",
                )
            )

        rollout = p.nSteps * par.numEnvs
        if rollout % p.batchSize != 0:
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="batch_divisor",
                    message=(
                        f"n_steps×num_envs ({rollout}) is not divisible by batch_size "
                        f"({p.batchSize}); SB3 may truncate the last minibatch."
                    ),
                )
            )

        if p.batchSize > rollout:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="batch_gt_rollout",
                    message="batch_size cannot exceed n_steps × num_envs.",
                )
            )

        physical = (
            max(1, self._model.machineProfile.cpuCountPhysical)
            if self._model.machineProfile
            else max(1, profile_machine().cpuCountPhysical)
        )
        par_errors, par_warnings = parallel_validation_issues(
            par,
            machine=self._model.machineProfile,
            physical_cores=physical,
        )
        for msg in par_errors:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="parallel_conflict",
                    message=msg,
                )
            )
        for msg in par_warnings:
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="parallel_warning",
                    message=msg,
                )
            )

        if self._model.machineProfile and not self._model.machineProfile.gpuAvailable:
            if p.device.value == "cuda":
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="cuda_without_gpu",
                        message="device is cuda but no GPU was detected on this machine.",
                    )
                )

        ckpt = self._model.checkpoint
        best = self._model.bestModel
        export_fmt = self._model.exportFormat

        if ckpt.enabled:
            if not ckpt.directory.strip():
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="checkpoint_dir",
                        message="checkpoint directory cannot be empty.",
                    )
                )
            elif ".." in ckpt.directory or ckpt.directory.startswith("/"):
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="checkpoint_dir_absolute",
                        message="checkpoint directory should be relative to the project folder.",
                    )
                )
            if not ckpt.filenameTemplate.strip():
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="checkpoint_template",
                        message="checkpoint filename_template cannot be empty.",
                    )
                )
            if ckpt.frequencySteps < 1:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="checkpoint_frequency",
                        message="frequency_steps must be at least 1.",
                    )
                )
            if ckpt.keepLastN < 0:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="checkpoint_keep",
                        message="keep_last_n cannot be negative.",
                    )
                )

        if best.enabled:
            if not best.directory.strip() or not best.filename.strip():
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="best_model_paths",
                        message="best_model directory and filename cannot be empty.",
                    )
                )
            if best.minImprovement < 0:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="best_model_improvement",
                        message="min_improvement cannot be negative.",
                    )
                )

        if not export_fmt.formats:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="export_formats_empty",
                    message="Select at least one export format.",
                )
            )

        json_like_selected = JSON_LIKE.intersection(set(export_fmt.formats))
        if json_like_selected and export_fmt.includeHeaderComments:
            labels = ", ".join(sorted(f.value for f in json_like_selected))
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="json_header_comments",
                    message=(
                        f"Header comments use // prefix for {labels} exports "
                        "(not valid strict JSON)."
                    ),
                )
            )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
