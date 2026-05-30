"""RL Trainer domain models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


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


class RewardTerm(BaseModel):
    id: str
    type: Literal["reward", "penalty"] = "reward"
    category: str = ""
    weight: float = 1.0
    enabled: bool = True
    params: dict[str, float] = Field(default_factory=dict)


class TerminationConfig(BaseModel):
    maxEpisodeSteps: int = 1000
    fallBaseHeightThreshold: float = 0.15
    maxTiltRad: float = 0.8
    maxJointTorque: Optional[float] = None
    timeoutTruncation: bool = True


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


class CurriculumAdvanceCriteria(BaseModel):
    """When met, the trainer may advance to the next curriculum stage."""

    minMeanEpisodeReward: float = 0.0
    minEpisodeLengthFrac: float = 0.7
    maxFallRate: float = 0.25
    minTimestepsInStage: Optional[int] = None


class CurriculumStage(BaseModel):
    id: str
    name: str
    order: int = 0
    description: str = ""
    timesteps: int = 300_000
    targetLinVelX: float = 0.0
    targetAngVelZ: float = 0.0
    rewardTerms: list[RewardTerm] = Field(default_factory=list)
    termination: TerminationConfig = Field(default_factory=TerminationConfig)
    advanceCriteria: CurriculumAdvanceCriteria = Field(
        default_factory=CurriculumAdvanceCriteria
    )


class CurriculumConfig(BaseModel):
    enabled: bool = False
    curriculumId: Optional[str] = None
    name: str = ""
    description: str = ""
    stages: list[CurriculumStage] = Field(default_factory=list)
    currentStageIndex: int = 0
    loadPreviousCheckpoint: bool = True
    resetPolicyOnStageAdvance: bool = False


class RlTrainerModel(BaseModel):
    id: str = Field(default_factory=new_id)
    projectName: str = ""
    robotName: str = "robot"
    version: str = "1.0"
    selectedPresetId: Optional[str] = None
    useRecommended: bool = True
    recommendationNotes: list[str] = Field(default_factory=list)
    machineProfile: Optional[MachineProfile] = None
    rewardTerms: list[RewardTerm] = Field(default_factory=list)
    termination: TerminationConfig = Field(default_factory=TerminationConfig)
    hyperparams: PpoHyperparams = Field(default_factory=PpoHyperparams)
    parallel: ParallelConfig = Field(default_factory=ParallelConfig)
    curriculum: CurriculumConfig = Field(default_factory=CurriculumConfig)
    customParams: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


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


class RecommendationResponse(BaseModel):
    hyperparams: PpoHyperparams
    parallel: ParallelConfig
    notes: list[str]
    machine: MachineProfile


class RlTrainerPatch(BaseModel):
    selectedPresetId: Optional[str] = None
    useRecommended: Optional[bool] = None
    rewardTerms: Optional[list[RewardTerm]] = None
    termination: Optional[TerminationConfig] = None
    hyperparams: Optional[PpoHyperparams] = None
    parallel: Optional[ParallelConfig] = None
    curriculum: Optional[CurriculumConfig] = None
    customParams: Optional[dict[str, Any]] = None


class HyperparamsPatch(BaseModel):
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
