"""Control editor domain models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return str(uuid4())


class TrainingProfile(str, Enum):
    PROFILE_A = "ProfileA"
    PROFILE_B = "ProfileB"
    PROFILE_C = "ProfileC"


# Simulation low-level controller for ProfileA (ros2_control plugin type key).
SIM_CONTROLLER_JOINT_TRAJECTORY = "joint_trajectory_controller"
SIM_CONTROLLER_FORWARD_COMMAND = "forward_command_controller"
DEFAULT_SIM_CONTROLLER = SIM_CONTROLLER_JOINT_TRAJECTORY


class JointControlConfig(BaseModel):
    name: str
    type: str  # revolute | prismatic | continuous
    childLinkName: str = ""
    lowerLimit: float = -3.14
    upperLimit: float = 3.14
    effort: float = 100.0
    velocity: float = 10.0
    commandInterface: str = "position"
    stateInterfaces: list[str] = Field(default_factory=lambda: ["position", "velocity", "effort"])
    kp: float = 50.0
    kd: float = 1.0
    defaultPosition: float = 0.0
    actionScale: float = 1.0
    enabled: bool = True
    profileParams: dict[str, Any] = Field(default_factory=dict)


class ControlModel(BaseModel):
    id: str = Field(default_factory=new_id)
    projectName: str = ""
    robotName: str = "robot"
    version: str = "1.0"
    sourceUrdf: str = ""
    trainingProfile: TrainingProfile = TrainingProfile.PROFILE_A
    simPlugin: str = "gz_ros2_control"
    hardwarePlugin: str = "gz_ros2_control/GazeboSimSystem"
    ros2Distro: str = "humble"
    controllerType: str = DEFAULT_SIM_CONTROLLER
    updateRate: int = 100
    actuatedJoints: list[JointControlConfig] = Field(default_factory=list)
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


def normalize_sim_controller(model: ControlModel) -> bool:
    """ProfileA uses joint_trajectory_controller for simulation. Returns True if updated."""
    if model.trainingProfile != TrainingProfile.PROFILE_A:
        return False
    if model.controllerType == DEFAULT_SIM_CONTROLLER:
        return False
    model.controllerType = DEFAULT_SIM_CONTROLLER
    return True
