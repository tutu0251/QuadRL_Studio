"""Tests for default pose utilities."""
from __future__ import annotations

from domain.models import Joint, JointType, Pose, RobotModel
from domain.pose_utils import DEFAULT_POSE_NAME, ensure_default_pose, export_default_pose_yaml, suggest_stand_joint_value


def test_ensure_default_pose_creates_stand_pose():
    j = Joint(name="fl_thigh_joint", type=JointType.REVOLUTE, parentLinkId="a", childLinkId="b")
    model = RobotModel(name="bot", joints=[j])
    ensure_default_pose(model, init_stand=True)
    assert model.poses
    assert model.defaultPoseId == model.poses[0].id
    assert model.poses[0].name == DEFAULT_POSE_NAME


def test_suggest_stand_joint_value_thigh():
    j = Joint(name="fl_thigh_joint", type=JointType.REVOLUTE, lowerLimit=-1.57, upperLimit=1.57)
    assert suggest_stand_joint_value(j) > 0.5


def test_export_default_pose_yaml_uses_joint_names():
    j = Joint(name="fl_hip_joint", type=JointType.REVOLUTE, defaultValue=0.1)
    model = RobotModel(name="bot", joints=[j])
    ensure_default_pose(model)
    doc = export_default_pose_yaml(model)
    assert "fl_hip_joint" in doc["joints"]
    assert doc["spawn"]["z"] == 0.5
