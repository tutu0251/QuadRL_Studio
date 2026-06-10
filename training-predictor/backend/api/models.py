"""Request/response models for the tuning API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StartTuningRequest(BaseModel):
    project: str
    # Resume an existing study by name (continue its Optuna DB); None ⇒ start a fresh study.
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


class StartTuningResponse(BaseModel):
    task_id: str
    study_name: str


class LogsResponse(BaseModel):
    entries: list[dict]
    next: int
