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
    workspace_ready: bool = False
    sensor_exports_ready: bool = False
    recommended_sim_backend: str = "mock"


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
    gazebo_headless: bool = True


class WorkspaceOperationRequest(BaseModel):
    clean: bool = False
    static_only: bool = False
    skip_runtime: bool = False
    skip_build: bool = False


class WorkspaceStatus(BaseModel):
    project: str
    state: Literal["idle", "starting", "running", "failed"] = "idle"
    operation: Optional[str] = None
    workspace_path: Optional[str] = None
    manifest_present: bool = False
    build_ready: bool = False
    exports_stale: bool = False
    stale_reasons: list[str] = Field(default_factory=list)
    readiness_status: Optional[str] = None
    training_ready: bool = False
    sensor_exports_ready: bool = False
    recommended_sim_backend: str = "mock"
    last_result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    finished_at: Optional[str] = None


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
    open_url: Optional[str] = None
    port: Optional[int] = None
    logdir: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None


class SystemStatsSample(BaseModel):
    sampledAt: str
    hostname: str
    cpuPercent: float
    cpuCountLogical: int
    ramTotalMb: int
    ramUsedMb: int
    ramAvailableMb: int
    ramUsedPercent: float
    ramTotalGb: float
    ramUsedGb: float
    gpuAvailable: bool
    gpuName: str
    gpuUtilPercent: Optional[float] = None
    gpuMemoryUsedMb: Optional[float] = None
    gpuMemoryTotalMb: Optional[float] = None
    gpuMemoryPercent: Optional[float] = None


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
