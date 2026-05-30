"""PPO planner domain models."""
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
    numEnvs: int = 1
    device: ComputeDevice = ComputeDevice.AUTO


class PpoPlannerModel(BaseModel):
    id: str = Field(default_factory=new_id)
    projectName: str = ""
    robotName: str = "robot"
    version: str = "1.0"
    params: PpoHyperparams = Field(default_factory=PpoHyperparams)
    useRecommended: bool = True
    machineProfile: Optional[MachineProfile] = None
    recommendationNotes: list[str] = Field(default_factory=list)
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
    numEnvs: Optional[int] = None
    device: Optional[ComputeDevice] = None
    useRecommended: Optional[bool] = None


class RecommendationResponse(BaseModel):
    params: PpoHyperparams
    notes: list[str]
    machine: MachineProfile
