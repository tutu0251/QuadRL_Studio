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
    recommended_sim_backend: str = "unavailable"


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
    recommended_sim_backend: str = "unavailable"
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
    rollout_count: Optional[int] = None
    episode_count: Optional[int] = None
    last_termination_reason: Optional[str] = None
    resume_checkpoint: Optional[str] = None
    dry_run: bool = False
    gazebo_headless: bool = True
    exit_code: Optional[int] = None
    command: Optional[str] = None


class CommandPreview(BaseModel):
    action: str
    command: str
    description: str = ""


class SpawnOffset(BaseModel):
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
    droll: float = 0.0
    dpitch: float = 0.0
    dyaw: float = 0.0


class SpawnConfig(BaseModel):
    project: str
    export_path: str
    pose_name: str = "Default Stand"
    base_spawn: dict[str, float] = Field(default_factory=dict)
    spawn_offset: SpawnOffset = Field(default_factory=SpawnOffset)
    effective_spawn: dict[str, float] = Field(default_factory=dict)
    joints: dict[str, float] = Field(default_factory=dict)
    controller_apply_delay_s: float = 25.0
    pose_confirmed: bool = False
    missing_export: bool = False


class SpawnConfigUpdate(BaseModel):
    spawn_offset: Optional[SpawnOffset] = None
    controller_apply_delay_s: Optional[float] = None
    pose_confirmed: Optional[bool] = None


class SpawnTestRequest(BaseModel):
    headless: bool = True


class SpawnTestStatus(BaseModel):
    project: str
    state: Literal["idle", "starting", "running", "stopping"] = "idle"
    headless: bool = True
    spawn_valid: bool = False
    pid: Optional[int] = None
    errors: list[str] = Field(default_factory=list)


class SpawnTestResult(BaseModel):
    project: str
    valid: bool
    status: str = "failed"
    state: Literal["idle", "starting", "running", "stopping"] = "idle"
    headless: bool = True
    pid: Optional[int] = None
    details: Optional[dict[str, Any]] = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    command: Optional[str] = None


class TopicEntry(BaseModel):
    key: str
    topic: str
    kind: str = "contact"
    bridge_present: bool = False
    runtime_status: Literal["ok", "failed", "pending"] = "pending"
    runtime_detail: Optional[str] = None
    confirmed: bool = False
    echo_command: str = ""


class TopicsBundle(BaseModel):
    project: str
    topics: list[TopicEntry] = Field(default_factory=list)
    confirmed_topics: list[str] = Field(default_factory=list)
    bridge_topic_count: int = 0
    observations_path: str = ""


class TopicsConfirmUpdate(BaseModel):
    confirmed_topics: list[str] = Field(default_factory=list)


class TopicWatchRequest(BaseModel):
    topics: list[str] = Field(default_factory=list)


class TopicEchoSample(BaseModel):
    ok: bool = False
    snippet: str = ""
    text: str = ""
    updated_at: str = ""


class TopicWatchStatus(BaseModel):
    project: str
    state: Literal["idle", "running"] = "idle"
    topics: list[str] = Field(default_factory=list)
    latest: dict[str, TopicEchoSample] = Field(default_factory=dict)


class ActionScaleEntry(BaseModel):
    joint: str
    action_scale: float
    default_position: float = 0.0


class ObservationScaleEntry(BaseModel):
    id: str
    key: str
    topic: str = ""
    scale: float = 1.0
    offset: float = 0.0
    clip_min: Optional[float] = None
    clip_max: Optional[float] = None
    enabled: bool = True


class TerminationSummary(BaseModel):
    stage_name: Optional[str] = None
    max_episode_steps: int = 1000
    fall_base_height_threshold: float = 0.25
    max_tilt_rad: float = 1.5
    enabled_term_ids: list[str] = Field(default_factory=list)


class TrainingConfig(BaseModel):
    project: str
    gains_path: str
    rl_config_path: str
    action_scales: list[ActionScaleEntry] = Field(default_factory=list)
    observation_scales: list[ObservationScaleEntry] = Field(default_factory=list)
    terminations: list[TerminationSummary] = Field(default_factory=list)
    curriculum_enabled: bool = False


class TrainingConfigUpdate(BaseModel):
    action_scales: Optional[list[ActionScaleEntry]] = None
    observation_scales: Optional[list[ObservationScaleEntry]] = None


class TensorBoardStatus(BaseModel):
    running: bool
    url: Optional[str] = None
    embed_url: Optional[str] = None
    open_url: Optional[str] = None
    port: Optional[int] = None
    logdir: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None


class DisplayStatus(BaseModel):
    gui_available: bool = False
    resolved_display: Optional[str] = None
    env_display: Optional[str] = None


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
