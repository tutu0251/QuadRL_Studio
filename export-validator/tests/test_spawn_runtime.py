"""Tests for geometry and physics spawn runtime validation."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from geometry_runtime import validate_geometry_runtime
from physics_runtime import validate_physics_runtime
from models import ValidationResult


def _write_geo_exports(tmp_path: Path, project: str = "bot") -> Path:
    exports = tmp_path / project / "exports"
    exports.mkdir(parents=True)
    (exports / f"geo_{project}.sdf").write_text("<sdf/>")
    (exports / f"geo_{project}.urdf").write_text("<robot name='bot'/>")
    return exports


def _write_phy_exports(tmp_path: Path, project: str = "bot") -> Path:
    exports = tmp_path / project / "exports"
    exports.mkdir(parents=True)
    (exports / f"phy_{project}.sdf").write_text("<sdf/>")
    (exports / f"phy_{project}.urdf").write_text("<robot name='bot'/>")
    return exports


def test_geometry_skipped_when_stack_unavailable(tmp_path: Path):
    exports = _write_geo_exports(tmp_path)
    with patch("spawn_runtime.check_spawn_stack", return_value={"available": False, "missing": ["ign"]}):
        result = validate_geometry_runtime(exports, "bot")
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"


def test_physics_skipped_when_stack_unavailable(tmp_path: Path):
    exports = _write_phy_exports(tmp_path)
    with patch("spawn_runtime.check_spawn_stack", return_value={"available": False, "missing": ["ign"]}):
        result = validate_physics_runtime(exports, "bot")
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"


def test_geometry_fails_when_export_missing(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    stack = {"available": True, "missing": [], "createPackage": "ros_gz_sim"}
    with patch("spawn_runtime.check_spawn_stack", return_value=stack):
        result = validate_geometry_runtime(exports, "bot")
    assert not result.valid
    assert any(e.code == "missing_geometry_export" for e in result.errors)


def test_physics_fails_when_export_missing(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    stack = {"available": True, "missing": [], "createPackage": "ros_gz_sim"}
    with patch("spawn_runtime.check_spawn_stack", return_value=stack):
        result = validate_physics_runtime(exports, "bot")
    assert not result.valid
    assert any(e.code == "missing_physics_export" for e in result.errors)


def test_geometry_prefers_sdf(tmp_path: Path):
    exports = _write_geo_exports(tmp_path)
    passed = ValidationResult(valid=True, details={"status": "passed", "durationS": 1.0})
    with patch("geometry_runtime.validate_spawn", return_value=passed) as spawn:
        result = validate_geometry_runtime(exports, "bot")
    assert result.valid
    spawn.assert_called_once()
    assert spawn.call_args.args[0].name.endswith(".sdf")


def test_physics_falls_back_to_urdf(tmp_path: Path):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    urdf = exports / "phy_bot.urdf"
    urdf.write_text("<robot/>")
    passed = ValidationResult(valid=True, details={"status": "passed"})
    with patch("physics_runtime.validate_spawn", return_value=passed) as spawn:
        result = validate_physics_runtime(exports, "bot")
    assert result.valid
    assert spawn.call_args.args[0] == urdf
