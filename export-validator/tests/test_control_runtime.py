"""Tests for control runtime validation."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from control_runtime import validate_control_runtime
from control_paths import ControlProjectPaths


def _write_control_exports(tmp_path: Path, project: str = "bot") -> Path:
    exports = tmp_path / project / "exports"
    exports.mkdir(parents=True)
    (exports / f"ctrl_{project}_ros2_control.urdf").write_text("<robot name='bot'/>")
    (exports / f"ctrl_{project}_controllers.yaml").write_text(
        "joint_trajectory_controller:\n  ros__parameters:\n    joints:\n      - hip\n"
    )
    (exports / f"ctrl_{project}_gains.yaml").write_text("gains: {}\n")
    return exports


def test_validate_skipped_when_stack_unavailable(tmp_path: Path):
    exports = _write_control_exports(tmp_path)
    with patch("control_runtime.check_control_runtime_stack", return_value={"available": False, "missing": ["ign"]}):
        result = validate_control_runtime(exports, "bot", auto_generate=False)
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"


def test_validate_skipped_when_no_workspace(tmp_path: Path):
    exports = _write_control_exports(tmp_path)
    stack = {"available": True, "missing": []}
    with patch("control_runtime.check_control_runtime_stack", return_value=stack):
        result = validate_control_runtime(exports, "bot", auto_generate=False, auto_build=False)
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"
    assert any(w.code == "control_runtime_no_workspace" for w in result.warnings)


def test_validate_fails_when_urdf_missing(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    stack = {"available": True, "missing": []}
    with patch("control_runtime.check_control_runtime_stack", return_value=stack):
        result = validate_control_runtime(exports, "bot", auto_generate=False)
    assert not result.valid
    assert any(e.code == "missing_control_export" for e in result.errors)


def test_validate_uses_workspace_when_ready(tmp_path: Path):
    exports = _write_control_exports(tmp_path)
    paths = ControlProjectPaths("bot", exports, projects_root=tmp_path)
    paths.workspace_dir.mkdir(parents=True)
    (paths.workspace_dir / "src").mkdir()
    (paths.workspace_dir / "install").mkdir(parents=True)
    setup = paths.install_setup()
    setup.write_text("# mock setup")

    runtime_result = {
        "status": "passed",
        "controllers": {"joint_state_broadcaster": "active"},
        "control_probe": {"joint": "hip", "moved": True},
        "errors": [],
    }
    stack = {"available": True, "missing": []}
    with (
        patch("control_runtime.check_control_runtime_stack", return_value=stack),
        patch("control_runtime.control_exports_stale", return_value=(False, [])),
        patch("control_runtime._run_runtime", return_value=runtime_result),
    ):
        result = validate_control_runtime(exports, "bot", auto_generate=False, auto_build=False)
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "passed"


@pytest.mark.integration
def test_control_runtime_live_if_available():
    from ev_ros_env import check_control_runtime_stack

    if not check_control_runtime_stack().get("available"):
        pytest.skip("Control runtime stack not installed")
    exports = Path.home() / "quadruped_dev_tool/projects/my_robot/exports"
    if not (exports / "ctrl_my_robot_ros2_control.urdf").is_file():
        pytest.skip("No control exports for my_robot")
    result = validate_control_runtime(exports, "my_robot", auto_generate=True, auto_build=True)
    assert result.details is not None
    assert result.details["status"] in ("passed", "failed", "skipped")
    if result.details["status"] == "passed":
        assert result.valid
