"""Tests for sensor runtime validation."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sensor_runtime import validate_sensor_runtime


def test_sensor_validate_skipped_when_stack_unavailable(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    with patch("sensor_runtime.check_sensor_runtime_stack", return_value={"available": False, "missing": ["colcon"]}):
        result = validate_sensor_runtime(exports, "bot")
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"


def test_sensor_validate_skipped_when_no_workspace(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    for name in ("sens_bot_rl.urdf", "sens_bot_bridge.yaml", "sens_bot_observations.yaml"):
        (exports / name).write_text("observations:\n  imu:\n    topic: /imu\n    kind: imu\n" if name.endswith("observations.yaml") else "x")
    stack = {"available": True, "missing": []}
    with patch("sensor_runtime.check_sensor_runtime_stack", return_value=stack):
        result = validate_sensor_runtime(exports, "bot", auto_generate=False, auto_build=False)
    assert result.valid
    assert any(w.code == "sensor_runtime_no_workspace" for w in result.warnings)


def test_sensor_validate_no_topics_skips(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    (exports / "sens_bot_rl.urdf").write_text("<robot/>")
    (exports / "sens_bot_bridge.yaml").write_text("bridges: []\n")
    (exports / "sens_bot_observations.yaml").write_text("observations: {}\n")
    stack = {"available": True, "missing": []}
    with patch("sensor_runtime.check_sensor_runtime_stack", return_value=stack):
        result = validate_sensor_runtime(exports, "bot", auto_generate=False)
    assert result.valid
    assert any(w.code == "sensor_runtime_no_topics" for w in result.warnings)


def test_sensor_validate_uses_workspace_when_ready(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    (exports / "sens_bot_rl.urdf").write_text("<robot/>")
    (exports / "sens_bot_bridge.yaml").write_text("bridges: []\n")
    (exports / "sens_bot_observations.yaml").write_text(
        "observations:\n  imu:\n    topic: /imu\n    kind: imu\n"
    )
    ws = tmp_path / "bot" / "workspace"
    (ws / "install").mkdir(parents=True)
    (ws / "install" / "setup.bash").write_text("# mock")
    (ws / "src").mkdir(parents=True)

    runtime_result = {
        "status": "passed",
        "errors": [],
        "topics": {"/imu": "ok"},
        "topic_list": ["/imu", "/joint_states"],
    }
    stack = {"available": True, "missing": []}
    with (
        patch("sensor_runtime.check_sensor_runtime_stack", return_value=stack),
        patch("sensor_runtime.pipeline_exports_stale", return_value=(False, [])),
        patch("sensor_runtime._run_sensor_runtime", return_value=runtime_result),
    ):
        result = validate_sensor_runtime(exports, "bot", auto_generate=False, auto_build=False)
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "passed"


def test_sensor_validate_fails_when_topic_missing_from_list(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    (exports / "sens_bot_rl.urdf").write_text("<robot/>")
    (exports / "sens_bot_bridge.yaml").write_text("bridges: []\n")
    (exports / "sens_bot_observations.yaml").write_text(
        "observations:\n  imu:\n    topic: /imu\n    kind: imu\n"
    )
    ws = tmp_path / "bot" / "workspace"
    (ws / "install").mkdir(parents=True)
    (ws / "install" / "setup.bash").write_text("# mock")
    (ws / "src").mkdir(parents=True)

    runtime_result = {
        "status": "failed",
        "errors": ["Topic /imu (imu) not in ros2 topic list"],
        "topics": {"/imu": "missing from topic list"},
        "topic_list": ["/joint_states"],
    }
    stack = {"available": True, "missing": []}
    with (
        patch("sensor_runtime.check_sensor_runtime_stack", return_value=stack),
        patch("sensor_runtime.pipeline_exports_stale", return_value=(False, [])),
        patch("sensor_runtime._run_sensor_runtime", return_value=runtime_result),
    ):
        result = validate_sensor_runtime(exports, "bot", auto_generate=False, auto_build=False)
    assert not result.valid
    assert result.details is not None
    assert result.details["status"] == "failed"


@pytest.mark.integration
def test_sensor_runtime_live_if_available():
    from ev_ros_env import check_sensor_runtime_stack

    if not check_sensor_runtime_stack().get("available"):
        pytest.skip("Sensor runtime stack not installed")
    exports = Path.home() / "quadruped_dev_tool/projects/my_robot/exports"
    if not (exports / "sens_my_robot_observations.yaml").is_file():
        pytest.skip("No sensor exports for my_robot")
    result = validate_sensor_runtime(exports, "my_robot", auto_generate=True, auto_build=True)
    assert result.details is not None
    assert result.details["status"] in ("passed", "failed", "skipped")
