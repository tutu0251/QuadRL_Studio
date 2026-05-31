"""Sensor editor domain models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return str(uuid4())


class SimTarget(str, Enum):
    GZ_FORTRESS = "gz_fortress"


class SensorKind(str, Enum):
    IMU = "imu"
    CONTACT = "contact"
    LIDAR = "lidar"
    ODOM = "odom"


class SensorPose(BaseModel):
    xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)


class ImuConfig(BaseModel):
    enableOrientation: bool = True


class ContactConfig(BaseModel):
    collisionName: str = "collision"


class LidarConfig(BaseModel):
    samples: int = 360
    minRange: float = 0.1
    maxRange: float = 30.0
    horizontalFov: float = 6.28318
    verticalSamples: int = 1


class OdomConfig(BaseModel):
    dimensions: int = 3
    odomFrame: str = ""
    robotBaseFrame: str = ""
    noiseStddev: float = 0.0


class SensorInstance(BaseModel):
    id: str = Field(default_factory=new_id)
    kind: SensorKind
    name: str
    parentLink: str
    enabled: bool = True
    pose: SensorPose = Field(default_factory=SensorPose)
    rosTopic: str = ""
    updateRate: float = 100.0
    imu: Optional[ImuConfig] = None
    contact: Optional[ContactConfig] = None
    lidar: Optional[LidarConfig] = None
    odom: Optional[OdomConfig] = None


class SensorModel(BaseModel):
    id: str = Field(default_factory=new_id)
    projectName: str = ""
    robotName: str = "robot"
    version: str = "1.0"
    sourceCtrlUrdf: str = ""
    simTarget: SimTarget = SimTarget.GZ_FORTRESS
    topicPrefix: str = "/quadruped"
    gzModelName: str = "robot"
    updateRateDefault: float = 100.0
    linkNames: list[str] = Field(default_factory=list)
    sensors: list[SensorInstance] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    entityType: Optional[str] = None
    entityId: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    details: Optional[dict[str, Any]] = None


class TaskLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class AsyncTaskStatus(BaseModel):
    task_id: str
    status: str
    logs: list[TaskLogEntry] = Field(default_factory=list)
    result: Optional[dict[str, Any]] = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SensorCreate(BaseModel):
    kind: SensorKind
    name: Optional[str] = None
    parentLink: str
    enabled: bool = True
    pose: Optional[SensorPose] = None
    rosTopic: Optional[str] = None
    updateRate: Optional[float] = None
    imu: Optional[ImuConfig] = None
    contact: Optional[ContactConfig] = None
    lidar: Optional[LidarConfig] = None
    odom: Optional[OdomConfig] = None


class SensorUpdate(BaseModel):
    name: Optional[str] = None
    parentLink: Optional[str] = None
    enabled: Optional[bool] = None
    pose: Optional[SensorPose] = None
    rosTopic: Optional[str] = None
    updateRate: Optional[float] = None
    imu: Optional[ImuConfig] = None
    contact: Optional[ContactConfig] = None
    lidar: Optional[LidarConfig] = None
    odom: Optional[OdomConfig] = None


class TopicConfigUpdate(BaseModel):
    topicPrefix: Optional[str] = None
    gzModelName: Optional[str] = None
    updateRateDefault: Optional[float] = None
