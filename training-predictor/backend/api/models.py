"""Request/response models for the tuning API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StartTuningRequest(BaseModel):
    project: str
    # "global" = one study, one shared param set (default). "sequential_stage" = a sub-study per
    # curriculum stage, each tuning that stage's own reward terms (see docs/PHASE1_SEQUENTIAL_TUNING.md).
    mode: str = "global"
    # Resume an existing study/sequence by name (continue its Optuna DB); None ⇒ start fresh.
    study_name: Optional[str] = None
    n_trials: int = Field(20, ge=1, le=1000)
    advisor_every_n: int = Field(5, ge=1)
    trial_timesteps: int = Field(30_000, ge=1)
    gazebo_headless: bool = True
    max_stages: Optional[int] = Field(None, ge=1)
    monitor_base_url: Optional[str] = None
    mock_objective: bool = False
    include_hyperparams: bool = True
    include_reward_weights: bool = True
    include_reward_params: bool = True
    trial_timeout: Optional[float] = None
    # ---- sequential_stage mode ----
    trials_per_stage: int = Field(10, ge=1, le=200)
    timesteps_per_stage: int = Field(30_000, ge=1)
    # Explicit 0-based stage indices to tune; if omitted, derived from max_stages (else all stages).
    stages_to_tune: Optional[list[int]] = None


class StartTuningResponse(BaseModel):
    task_id: str
    study_name: str


class LogsResponse(BaseModel):
    entries: list[dict]
    next: int
