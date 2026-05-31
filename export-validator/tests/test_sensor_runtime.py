"""Tests for sensor runtime validation."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sensor_runtime import validate_sensor_runtime


def test_sensor_validate_skipped_when_stack_unavailable(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    with patch("sensor_runtime.check_control_runtime_stack", return_value={"available": False, "missing": ["colcon"]}):
        result = validate_sensor_runtime(exports, "bot")
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"


def test_sensor_validate_skipped_when_no_workspace(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    (exports / "sens_bot_observations.yaml").write_text("observations:\n  imu:\n    topic: /imu\n")
    stack = {"available": True, "missing": []}
    with patch("sensor_runtime.check_control_runtime_stack", return_value=stack):
        result = validate_sensor_runtime(exports, "bot")
    assert result.valid
    assert any(w.code == "sensor_runtime_no_workspace" for w in result.warnings)


def test_sensor_validate_no_topics_skips(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    (exports / "sens_bot_observations.yaml").write_text("observations: {}\n")
    ws = tmp_path / "bot" / "workspace"
    (ws / "install").mkdir(parents=True)
    (ws / "install" / "setup.bash").write_text("# mock")
    stack = {"available": True, "missing": []}
    with patch("sensor_runtime.check_control_runtime_stack", return_value=stack):
        result = validate_sensor_runtime(exports, "bot")
    assert result.valid
    assert any(w.code == "sensor_runtime_no_topics" for w in result.warnings)


def test_sensor_validate_uses_workspace_when_ready(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    (exports / "sens_bot_observations.yaml").write_text(
        "observations:\n  imu:\n    topic: /imu\n    kind: imu\n"
    )
    ws = tmp_path / "bot" / "workspace"
    (ws / "install").mkdir(parents=True)
    (ws / "install" / "setup.bash").write_text("# mock")

    runtime_result = {"status": "ready", "errors": [], "topics": {"/imu": "ok"}}
    stack = {"available": True, "missing": []}
    with (
        patch("sensor_runtime.check_control_runtime_stack", return_value=stack),
        patch("sensor_runtime._import_validate_runtime") as import_runtime,
    ):
        import_runtime.return_value = lambda *_args, **_kwargs: runtime_result
        result = validate_sensor_runtime(exports, "bot")
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "passed"


@pytest.mark.integration
def test_sensor_runtime_live_if_available():
    from ev_ros_env import check_control_runtime_stack

    if not check_control_runtime_stack().get("available"):
        pytest.skip("Sensor runtime stack not installed")
    exports = Path.home() / "quadruped_dev_tool/projects/my_robot/exports"
    if not (exports / "sens_my_robot_observations.yaml").is_file():
        pytest.skip("No sensor exports for my_robot")
    result = validate_sensor_runtime(exports, "my_robot")
    assert result.details is not None
    assert result.details["status"] in ("passed", "failed", "skipped")
