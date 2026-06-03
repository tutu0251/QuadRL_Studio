"""URDF-first robot geometry data models."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return str(uuid4())


class PrimitiveType(str, Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    SPHERE = "sphere"
    CAPSULE = "capsule"


class JointType(str, Enum):
    FIXED = "fixed"
    REVOLUTE = "revolute"
    CONTINUOUS = "continuous"
    PRISMATIC = "prismatic"


class NamingConvention(str, Enum):
    ROS2_UPPER = "ROS2_UPPER"  # FL_hip_joint
    LOWER = "LOWER"  # fl_hip_joint


class Vec3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Quat(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0


class Frame(BaseModel):
    position: Vec3 = Field(default_factory=Vec3)
    rotation: Quat = Field(default_factory=Quat)


class Inertial(BaseModel):
    mass: float = 1.0
    com: Vec3 = Field(default_factory=Vec3)
    ixx: float = 0.01
    iyy: float = 0.01
    izz: float = 0.01


class PrimitiveShape(BaseModel):
    id: str = Field(default_factory=new_id)
    type: PrimitiveType = PrimitiveType.BOX
    dimensions: list[float] = Field(default_factory=lambda: [0.1, 0.1, 0.1])
    localPosition: Vec3 = Field(default_factory=Vec3)
    localRotation: Quat = Field(default_factory=Quat)
    color: str = "#808080"
    material: str = "default"


class Link(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str = "link"
    parentJointId: Optional[str] = None
    shapes: list[PrimitiveShape] = Field(default_factory=list)
    frame: Frame = Field(default_factory=Frame)
    inertial: Inertial = Field(default_factory=Inertial)


class Joint(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str = "joint"
    parentLinkId: str = ""
    childLinkId: str = ""
    type: JointType = JointType.FIXED
    originPosition: Vec3 = Field(default_factory=Vec3)
    originRotation: Quat = Field(default_factory=Quat)
    axis: Vec3 = Field(default_factory=lambda: Vec3(x=0, y=0, z=1))
    lowerLimit: float = -3.14
    upperLimit: float = 3.14
    defaultValue: float = 0.0


class Pose(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str = "default"
    jointValues: dict[str, float] = Field(default_factory=dict)


class RobotModel(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str = "robot"
    version: str = "2.0"
    links: list[Link] = Field(default_factory=list)
    joints: list[Joint] = Field(default_factory=list)
    poses: list[Pose] = Field(default_factory=list)
    defaultPoseId: Optional[str] = None
    templates: list[str] = Field(default_factory=list)
    namingConvention: NamingConvention = NamingConvention.LOWER
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    entityType: Optional[str] = None
    entityId: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class TaskLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class AsyncTaskStatus(BaseModel):
    task_id: str
    status: str
    logs: list[TaskLogEntry] = Field(default_factory=list)
    result: Optional[dict[str, Any]] = None


class MeasurementResult(BaseModel):
    tool: str
    value: float
    unit: str = "m"
    label: str = ""
    points: list[Vec3] = Field(default_factory=list)
