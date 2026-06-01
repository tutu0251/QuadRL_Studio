"""Pydantic models for Train Monitor API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ExportFileInfo(BaseModel):
    category: str
    filename: str
    path: str
    size_bytes: int
    modified_at: str
    format: str


class ExportBundle(BaseModel):
    project: str
    exports_dir: str
    files: list[ExportFileInfo]
    missing_required: list[str] = Field(default_factory=list)
    ready_for_training: bool = False


class CheckpointInfo(BaseModel):
    path: str
    filename: str
    size_bytes: int
    modified_at: str


class RunStageInfo(BaseModel):
    name: str
    logdir: str
    has_events: bool


class RunInfo(BaseModel):
    run_id: str
    path: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    status: Literal["running", "completed", "failed", "stopped", "unknown"] = "unknown"
    config: Optional[str] = None
    tensorboard_logdir: Optional[str] = None
    curriculum_enabled: bool = False
    stages: list[RunStageInfo] = Field(default_factory=list)
    pid: Optional[int] = None


class ScalarSeries(BaseModel):
    tag: str
    steps: list[int]
    values: list[float]


class TrainStartRequest(BaseModel):
    dry_run: bool = False
    resume_checkpoint: Optional[str] = None
    config_path: Optional[str] = None


class TrainStatus(BaseModel):
    project: str
    state: Literal["idle", "starting", "running", "stopping", "failed"]
    pid: Optional[int] = None
    run_id: Optional[str] = None
    started_at: Optional[str] = None
    current_stage: Optional[str] = None
    progress_message: Optional[str] = None
    resume_checkpoint: Optional[str] = None
    dry_run: bool = False
    exit_code: Optional[int] = None


class TensorBoardStatus(BaseModel):
    running: bool
    url: Optional[str] = None
    embed_url: Optional[str] = None
    port: Optional[int] = None
    logdir: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None


class ProjectSummary(BaseModel):
    name: str
    has_rl_export: bool
    has_ppo_export: bool
    export_count: int
    checkpoint_count: int
    run_count: int
    training_state: str


class TaskLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class AsyncTaskStatus(BaseModel):
    task_id: str
    status: str
    logs: list[TaskLogEntry] = Field(default_factory=list)
    result: Optional[dict[str, Any]] = None
