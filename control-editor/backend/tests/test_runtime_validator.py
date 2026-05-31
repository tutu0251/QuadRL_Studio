"""Tests for control export validation via export-validator."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from validator.runtime_validator import EXPORT_VALIDATOR_BACKEND, validate_control_export


def test_validate_skipped_when_export_validator_unavailable(tmp_path: Path):
    missing_backend = tmp_path / "missing"
    with patch("validator.runtime_validator.EXPORT_VALIDATOR_BACKEND", missing_backend):
        result = validate_control_export("bot")
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"
    assert any(w.code == "export_validation_skipped" for w in result.warnings)


def test_validate_fails_when_exports_dir_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "validator.runtime_validator.project_storage.project_dir",
        lambda name: tmp_path / name,
    )
    with patch("validator.runtime_validator.EXPORT_VALIDATOR_BACKEND", EXPORT_VALIDATOR_BACKEND):
        result = validate_control_export("bot")
    assert not result.valid
    assert any(e.code == "missing_exports_dir" for e in result.errors)


def test_validate_maps_runtime_passed(tmp_path: Path, monkeypatch):
    exports = tmp_path / "bot" / "exports"
    exports.mkdir(parents=True)
    monkeypatch.setattr(
        "validator.runtime_validator.project_storage.project_dir",
        lambda name: tmp_path / name,
    )

    runtime_result = type(
        "R",
        (),
        {
            "valid": True,
            "errors": [],
            "warnings": [],
            "details": {"status": "passed", "durationS": 1.0},
        },
    )()

    mock_module = type("control_runtime", (), {"validate_control_runtime": lambda *a, **k: runtime_result})()
    with patch("validator.runtime_validator.EXPORT_VALIDATOR_BACKEND", EXPORT_VALIDATOR_BACKEND):
        with patch.dict("sys.modules", {"control_runtime": mock_module}):
            result = validate_control_export("bot")

    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "passed"
