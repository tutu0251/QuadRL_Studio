"""Tests for gz_ros2_control URDF / YAML export."""
from __future__ import annotations

import tempfile
from pathlib import Path

from domain.control_core import ControlCore
from domain.models import (
    DEFAULT_HARDWARE_PLUGIN,
    DEFAULT_SIM_PLUGIN_CLASS,
    DEFAULT_SIM_PLUGIN_FILENAME,
    ControlModel,
    normalize_gazebo_plugin,
)
from exporter.ros2_control_exporter import export_all
from storage import project_storage

_MINIMAL_PHY_URDF = """<?xml version="1.0"?>
<robot name="test_bot">
  <link name="base">
    <inertial><mass value="5"/><inertia ixx="0.1" iyy="0.1" izz="0.1"/></inertial>
  </link>
  <link name="leg">
    <inertial><mass value="1"/><inertia ixx="0.01" iyy="0.01" izz="0.01"/></inertial>
  </link>
  <joint name="hip_joint" type="revolute">
    <parent link="base"/><child link="leg"/>
    <axis xyz="0 1 0"/><limit lower="-1" upper="1" effort="20" velocity="5"/>
  </joint>
</robot>
"""


def _setup_project(tmp: Path, name: str = "robot") -> Path:
    project_storage.PROJECTS_ROOT = tmp
    root = tmp / name / "exports"
    root.mkdir(parents=True)
    (root / f"phy_{name}.urdf").write_text(_MINIMAL_PHY_URDF)
    return root / f"phy_{name}.urdf"


def test_export_uses_official_gz_ros2_control_plugin():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = "robot"
        phy = _setup_project(tmp, proj)
        model = ControlCore().import_phy_urdf(proj)
        urdf_out = project_storage.export_ros2_urdf_path(proj)
        ctrl_out = project_storage.export_controllers_yaml_path(proj)
        gains_out = project_storage.export_gains_yaml_path(proj)
        export_all(model, phy, urdf_out, ctrl_out, gains_out)
        text = urdf_out.read_text()
        assert DEFAULT_SIM_PLUGIN_FILENAME in text
        assert DEFAULT_SIM_PLUGIN_CLASS in text
        assert DEFAULT_HARDWARE_PLUGIN in text
        assert "gz_ros2_control/gz_ros2_control_system" not in text
        assert 'name="gz_ros2_control"' not in text or DEFAULT_SIM_PLUGIN_CLASS in text
        yaml_text = ctrl_out.read_text()
        assert "joint_trajectory_controller/JointTrajectoryController" in yaml_text


def test_normalize_gazebo_plugin_migrates_legacy_filename():
    model = ControlModel(
        simPluginFilename="gz_ros2_control/gz_ros2_control_system",
        simPluginClass="gz_ros2_control",
    )
    assert normalize_gazebo_plugin(model)
    assert model.simPluginFilename == DEFAULT_SIM_PLUGIN_FILENAME
    assert model.simPluginClass == DEFAULT_SIM_PLUGIN_CLASS
