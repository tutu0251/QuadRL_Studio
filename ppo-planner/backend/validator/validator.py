"""Validate PPO hyperparameters before export."""
from __future__ import annotations

from domain.models import PpoPlannerModel, ValidationIssue, ValidationResult


class PpoValidator:
    def __init__(self, model: PpoPlannerModel):
        self._model = model

    def validate(self) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        p = self._model.params

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
        if p.numEnvs < 1:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="num_envs_min",
                    message="num_envs must be at least 1.",
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

        rollout = p.nSteps * p.numEnvs
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

        if self._model.machineProfile and not self._model.machineProfile.gpuAvailable:
            if p.device.value == "cuda":
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="cuda_without_gpu",
                        message="device is cuda but no GPU was detected on this machine.",
                    )
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
