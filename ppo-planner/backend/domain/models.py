"""PPO planner domain models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def new_id() -> str:
    return str(uuid4())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ComputeDevice(str, Enum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


class VecEnvType(str, Enum):
    DUMMY = "dummy"
    SUBPROC = "subproc"


class MachineProfile(BaseModel):
    hostname: str = ""
    platform: str = ""
    cpuCountLogical: int = 1
    cpuCountPhysical: int = 1
    ramGb: float = 0.0
    gpuAvailable: bool = False
    gpuName: str = ""
    vramGb: float = 0.0
    profiledAt: str = Field(default_factory=utc_now_iso)


class PpoHyperparams(BaseModel):
    learningRate: float = 3e-4
    nSteps: int = 2048
    batchSize: int = 64
    nEpochs: int = 10
    gamma: float = 0.99
    gaeLambda: float = 0.95
    clipRange: float = 0.2
    entCoef: float = 0.0
    vfCoef: float = 0.5
    maxGradNorm: float = 0.5
    totalTimesteps: int = 1_000_000
    device: ComputeDevice = ComputeDevice.AUTO


class ParallelConfig(BaseModel):
    numEnvs: int = 1
    vecEnvType: VecEnvType = VecEnvType.SUBPROC
    nProc: Optional[int] = None


class CheckpointFrequency(str, Enum):
    END_ONLY = "end_only"
    STEPS = "steps"
    ROLLOUT = "rollout"


class CheckpointConfig(BaseModel):
    enabled: bool = True
    directory: str = "checkpoints"
    frequency: CheckpointFrequency = CheckpointFrequency.END_ONLY
    frequencySteps: int = 50_000
    keepLastN: int = 5
    filenameTemplate: str = "ppo_{stage_id}"
    saveOnInterrupt: bool = True


class BestModelMetric(str, Enum):
    MEAN_EPISODE_REWARD = "mean_episode_reward"
    MEAN_EPISODE_LENGTH = "mean_episode_length"
    ROLLING_MEAN_REWARD = "rolling_mean_reward"


class BestModelMode(str, Enum):
    MAX = "max"
    MIN = "min"


class BestModelConfig(BaseModel):
    enabled: bool = True
    metric: BestModelMetric = BestModelMetric.MEAN_EPISODE_REWARD
    mode: BestModelMode = BestModelMode.MAX
    directory: str = "checkpoints"
    filename: str = "best_model"
    minImprovement: float = 0.0


class ExportConfigFormat(str, Enum):
    YAML = "yaml"
    JSON = "json"
    JSON_MIN = "json_min"
    TOML = "toml"


class ExportFormatConfig(BaseModel):
    formats: list[ExportConfigFormat] = Field(
        default_factory=lambda: [ExportConfigFormat.YAML]
    )
    includeMachineProfile: bool = True
    includeRecommendationNotes: bool = True
    includeHeaderComments: bool = True
    sortKeys: bool = False

    @classmethod
    def _normalize_formats(cls, values: list[ExportConfigFormat]) -> list[ExportConfigFormat]:
        seen: set[ExportConfigFormat] = set()
        out: list[ExportConfigFormat] = []
        for fmt in values:
            if fmt not in seen:
                seen.add(fmt)
                out.append(fmt)
        return out

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_format_field(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "format" in data and "formats" not in data:
            legacy = data.pop("format")
            data["formats"] = [legacy] if legacy else ["yaml"]
        return data

    @model_validator(mode="after")
    def dedupe_formats(self) -> ExportFormatConfig:
        object.__setattr__(self, "formats", self._normalize_formats(list(self.formats)))
        return self


class PpoPlannerModel(BaseModel):
    id: str = Field(default_factory=new_id)
    projectName: str = ""
    robotName: str = "robot"
    version: str = "1.0"
    params: PpoHyperparams = Field(default_factory=PpoHyperparams)
    parallel: ParallelConfig = Field(default_factory=ParallelConfig)
    checkpoint: CheckpointConfig = Field(default_factory=CheckpointConfig)
    bestModel: BestModelConfig = Field(default_factory=BestModelConfig)
    exportFormat: ExportFormatConfig = Field(default_factory=ExportFormatConfig)
    useRecommended: bool = True
    machineProfile: Optional[MachineProfile] = None
    recommendationNotes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_num_envs(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        params = data.get("params")
        if isinstance(params, dict) and "numEnvs" in params:
            legacy = params.pop("numEnvs")
            parallel = data.get("parallel")
            if not isinstance(parallel, dict):
                data["parallel"] = {
                    "numEnvs": legacy,
                    "vecEnvType": "subproc" if legacy > 1 else "dummy",
                    "nProc": None,
                }
            elif parallel.get("numEnvs", 1) == 1:
                parallel["numEnvs"] = legacy
        if "parallel" not in data:
            data["parallel"] = {
                "numEnvs": 1,
                "vecEnvType": "subproc",
                "nProc": None,
            }
        if "checkpoint" not in data:
            data["checkpoint"] = CheckpointConfig().model_dump()
        if "bestModel" not in data:
            data["bestModel"] = BestModelConfig().model_dump()
        if "exportFormat" not in data:
            data["exportFormat"] = ExportFormatConfig().model_dump()
        return data


class ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class TaskLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class AsyncTaskStatus(BaseModel):
    task_id: str
    status: str
    logs: list[TaskLogEntry] = Field(default_factory=list)
    result: Optional[dict[str, Any]] = None


class PpoParamsUpdate(BaseModel):
    learningRate: Optional[float] = None
    nSteps: Optional[int] = None
    batchSize: Optional[int] = None
    nEpochs: Optional[int] = None
    gamma: Optional[float] = None
    gaeLambda: Optional[float] = None
    clipRange: Optional[float] = None
    entCoef: Optional[float] = None
    vfCoef: Optional[float] = None
    maxGradNorm: Optional[float] = None
    totalTimesteps: Optional[int] = None
    device: Optional[ComputeDevice] = None
    useRecommended: Optional[bool] = None


class ParallelPatch(BaseModel):
    numEnvs: Optional[int] = None
    vecEnvType: Optional[VecEnvType] = None
    nProc: Optional[int] = None
    useRecommended: Optional[bool] = None


class CheckpointPatch(BaseModel):
    enabled: Optional[bool] = None
    directory: Optional[str] = None
    frequency: Optional[CheckpointFrequency] = None
    frequencySteps: Optional[int] = None
    keepLastN: Optional[int] = None
    filenameTemplate: Optional[str] = None
    saveOnInterrupt: Optional[bool] = None


class BestModelPatch(BaseModel):
    enabled: Optional[bool] = None
    metric: Optional[BestModelMetric] = None
    mode: Optional[BestModelMode] = None
    directory: Optional[str] = None
    filename: Optional[str] = None
    minImprovement: Optional[float] = None


class ExportFormatPatch(BaseModel):
    formats: Optional[list[ExportConfigFormat]] = None
    includeMachineProfile: Optional[bool] = None
    includeRecommendationNotes: Optional[bool] = None
    includeHeaderComments: Optional[bool] = None
    sortKeys: Optional[bool] = None


class OutputPatch(BaseModel):
    checkpoint: Optional[CheckpointPatch] = None
    bestModel: Optional[BestModelPatch] = None
    exportFormat: Optional[ExportFormatPatch] = None


class RecommendationResponse(BaseModel):
    params: PpoHyperparams
    parallel: ParallelConfig
    notes: list[str]
    machine: MachineProfile
