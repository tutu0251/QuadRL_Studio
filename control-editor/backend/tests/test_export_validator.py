"""Tests for export file validation."""
from __future__ import annotations

import tempfile
from pathlib import Path

from domain.control_core import ControlCore
from exporter.ros2_control_exporter import export_all
from storage import project_storage
from validator.export_validator import validate_export_files

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


def _export_paths(proj: str) -> tuple[Path, Path, Path]:
    return (
        project_storage.export_ros2_urdf_path(proj),
        project_storage.export_controllers_yaml_path(proj),
        project_storage.export_gains_yaml_path(proj),
    )


def test_export_validator_passes_on_fresh_export():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = "robot"
        phy = _setup_project(tmp, proj)
        model = ControlCore().import_phy_urdf(proj)
        urdf_out, ctrl_out, gains_out = _export_paths(proj)
        export_all(model, phy, urdf_out, ctrl_out, gains_out)

        result = validate_export_files(model, urdf_out, ctrl_out, gains_out)
        assert result.valid, result.errors
        assert result.details is not None
        assert result.details["expectedJointCount"] == 1
        assert result.details["urdfJointCount"] == 1
        assert result.details["controllerJointCount"] == 1
        assert result.details["gainsJointCount"] == 1


def test_export_validator_fails_when_files_missing():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = "robot"
        _setup_project(tmp, proj)
        model = ControlCore().import_phy_urdf(proj)
        urdf_out, ctrl_out, gains_out = _export_paths(proj)

        result = validate_export_files(model, urdf_out, ctrl_out, gains_out)
        assert not result.valid
        codes = {e.code for e in result.errors}
        assert "missing_urdf_file" in codes
        assert "missing_controllers_file" in codes
        assert "missing_gains_file" in codes


def test_export_validator_fails_on_kp_mismatch():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = "robot"
        phy = _setup_project(tmp, proj)
        model = ControlCore().import_phy_urdf(proj)
        urdf_out, ctrl_out, gains_out = _export_paths(proj)
        export_all(model, phy, urdf_out, ctrl_out, gains_out)

        joint = next(j for j in model.actuatedJoints if j.enabled)
        text = gains_out.read_text().replace(f"kp: {joint.kp}", "kp: 999.0", 1)
        gains_out.write_text(text)

        result = validate_export_files(model, urdf_out, ctrl_out, gains_out)
        assert not result.valid
        assert any(e.code == "gains_kp_mismatch" for e in result.errors)
