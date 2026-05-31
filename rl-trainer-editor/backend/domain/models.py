"""RL Trainer domain models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return str(uuid4())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=new_id)
    projectName: str = ""
    robotName: str = "robot"
    version: str = "1.0"
    selectedPresetId: Optional[str] = None
    recommendationNotes: list[str] = Field(default_factory=list)
    machineProfile: Optional[MachineProfile] = None
    rewardTerms: list[RewardTerm] = Field(default_factory=list)
    termination: TerminationConfig = Field(default_factory=TerminationConfig)
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


class RlTrainerPatch(BaseModel):
    selectedPresetId: Optional[str] = None
    rewardTerms: Optional[list[RewardTerm]] = None
    termination: Optional[TerminationConfig] = None
    curriculum: Optional[CurriculumConfig] = None
    customParams: Optional[dict[str, Any]] = None
