"""
FROZEN CONTRACT TEST — DO NOT MODIFY

This file asserts that sensor export and URDF patching never rename links or
alter foot-contact joint parent/child relationships. Update export code to
satisfy this contract; do not change this test to match broken exports.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
_WS_BACKEND = Path(__file__).resolve().parents[3] / "workspace-generator" / "backend"
for path in (_BACKEND, _WS_BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from domain.models import (  # noqa: E402
    ContactConfig,
    OdomConfig,
    SensorCreate,
    SensorKind,
    SensorModel,
)
from domain.sensor_core import SensorCore  # noqa: E402
from exporter.sensor_urdf_exporter import merge_sensors_into_urdf  # noqa: E402
from generator.link_preservation import extract_link_topology  # noqa: E402
from generator.urdf_patch import patch_contact_sensors  # noqa: E402

# --- frozen fixture: quadruped leg chain with foot fixed joints ---
FROZEN_CTRL_URDF = """<?xml version='1.0'?>
<robot name="qrl_contract_bot">
  <link name="base_link"/>
  <link name="fl_calf_link"/>
  <link name="fl_foot_link"/>
  <link name="fr_calf_link"/>
  <link name="fr_foot_link"/>
  <link name="rl_calf_link"/>
  <link name="rl_foot_link"/>
  <link name="rr_calf_link"/>
  <link name="rr_foot_link"/>
  <joint name="fl_ankle_joint" type="fixed">
    <parent link="fl_calf_link"/>
    <child link="fl_foot_link"/>
  </joint>
  <joint name="fr_ankle_joint" type="fixed">
    <parent link="fr_calf_link"/>
    <child link="fr_foot_link"/>
  </joint>
  <joint name="rl_ankle_joint" type="fixed">
    <parent link="rl_calf_link"/>
    <child link="rl_foot_link"/>
  </joint>
  <joint name="rr_ankle_joint" type="fixed">
    <parent link="rr_calf_link"/>
    <child link="rr_foot_link"/>
  </joint>
  <gazebo>
    <plugin filename="libgz_ros2_control-system.so" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
      <parameters>ctrl_qrl_contract_bot_controllers.yaml</parameters>
    </plugin>
  </gazebo>
</robot>"""

FROZEN_LINK_NAMES = (
    "base_link",
    "fl_calf_link",
    "fl_foot_link",
    "fr_calf_link",
    "fr_foot_link",
    "rl_calf_link",
    "rl_foot_link",
    "rr_calf_link",
    "rr_foot_link",
)

FROZEN_FOOT_JOINTS = (
    ("fl_ankle_joint", "fixed", "fl_calf_link", "fl_foot_link"),
    ("fr_ankle_joint", "fixed", "fr_calf_link", "fr_foot_link"),
    ("rl_ankle_joint", "fixed", "rl_calf_link", "rl_foot_link"),
    ("rr_ankle_joint", "fixed", "rr_calf_link", "rr_foot_link"),
)


def _build_frozen_sensor_model() -> SensorModel:
    core = SensorCore(
        SensorModel(
            projectName="qrl_contract_bot",
            robotName="qrl_contract_bot",
            gzModelName="qrl_contract_bot",
            topicPrefix="/qrl_contract_bot",
            linkNames=list(FROZEN_LINK_NAMES),
        )
    )
    core.add_sensor(
        SensorCreate(kind=SensorKind.IMU, name="base_imu", parentLink="base_link")
    )
    for foot in ("fl_foot_link", "fr_foot_link", "rl_foot_link", "rr_foot_link"):
        core.add_sensor(
            SensorCreate(
                kind=SensorKind.CONTACT,
                name=f"{foot}_contact",
                parentLink=foot,
                contact=ContactConfig(),
            )
        )
    core.add_sensor(
        SensorCreate(
            kind=SensorKind.ODOM,
            name="base_link_odom",
            parentLink="base_link",
            odom=OdomConfig(robotBaseFrame="base_link"),
        )
    )
    return core.get_model()


def _foot_joints(topo) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        j for j in topo.joints if j[1] == "fixed" and "foot" in j[3].lower()
    )


@pytest.fixture()
def frozen_ctrl_urdf(tmp_path: Path) -> Path:
    path = tmp_path / "ctrl_qrl_contract_bot_ros2_control.urdf"
    path.write_text(FROZEN_CTRL_URDF, encoding="utf-8")
    return path


def test_export_preserves_link_names_and_foot_joint_parents(frozen_ctrl_urdf: Path, tmp_path: Path):
    model = _build_frozen_sensor_model()
    source_root = ET.fromstring(FROZEN_CTRL_URDF)
    source_topo = extract_link_topology(source_root)

    assert source_topo.link_names == FROZEN_LINK_NAMES
    assert _foot_joints(source_topo) == FROZEN_FOOT_JOINTS

    out_path = tmp_path / "sens_qrl_contract_bot_rl.urdf"
    merge_sensors_into_urdf(model, frozen_ctrl_urdf, out_path)
    merged_text = out_path.read_text(encoding="utf-8")
    patched_text = patch_contact_sensors(merged_text)

    final_root = ET.fromstring(patched_text)
    final_topo = extract_link_topology(final_root)

    assert final_topo.link_names == FROZEN_LINK_NAMES
    assert _foot_joints(final_topo) == FROZEN_FOOT_JOINTS
    assert "fixed_joint_lump" not in patched_text

    for foot in ("fl_foot_link", "fr_foot_link", "rl_foot_link", "rr_foot_link"):
        assert f'reference="{foot}"' in patched_text
        assert f"{foot}_contact" in patched_text

    assert 'name="ignition::gazebo::systems::OdometryPublisher"' in patched_text
    assert "<robot_base_frame>base_link</robot_base_frame>" in patched_text
