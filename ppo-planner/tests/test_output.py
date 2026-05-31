"""Tests for output config validation and export."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from domain.models import (
    CheckpointConfig,
    ExportConfigFormat,
    ExportFormatConfig,
    PpoPlannerModel,
)
from exporter.ppo_yaml_exporter import build_ppo_config_body, export_ppo_config, export_ppo_configs
from validator.validator import PpoValidator


def test_export_includes_checkpoint_and_best_model():
    model = PpoPlannerModel(projectName="demo", robotName="robot")
    body = build_ppo_config_body(model, "demo")
    assert "checkpoint" in body
    assert "best_model" in body
    assert body["checkpoint"]["directory"] == "checkpoints"
    assert body["best_model"]["filename"] == "best_model"


def test_json_export_format(tmp_path, monkeypatch):
    import storage.project_storage as ps

    monkeypatch.setattr(ps, "PROJECTS_ROOT", tmp_path)
    model = PpoPlannerModel(
        projectName="demo",
        robotName="robot",
        exportFormat=ExportFormatConfig(
            formats=[ExportConfigFormat.JSON],
            includeHeaderComments=False,
        ),
    )
    path = export_ppo_config(model, "demo", ExportConfigFormat.JSON)
    assert path.name == "ppo_demo_config.json"
    data = json.loads(path.read_text())
    assert data["project"] == "demo"


def test_multi_format_export(tmp_path, monkeypatch):
    import storage.project_storage as ps

    monkeypatch.setattr(ps, "PROJECTS_ROOT", tmp_path)
    model = PpoPlannerModel(
        projectName="demo",
        robotName="robot",
        exportFormat=ExportFormatConfig(
            formats=[
                ExportConfigFormat.YAML,
                ExportConfigFormat.JSON,
                ExportConfigFormat.TOML,
            ],
            includeHeaderComments=False,
        ),
    )
    paths = export_ppo_configs(model, "demo")
    assert len(paths) == 3
    names = {p.name for p in paths}
    assert "ppo_demo_config.yaml" in names
    assert "ppo_demo_config.json" in names
    assert "ppo_demo_config.toml" in names


def test_validator_rejects_empty_formats():
    model = PpoPlannerModel(
        projectName="demo",
        exportFormat=ExportFormatConfig(formats=[]),
    )
    result = PpoValidator(model).validate()
    assert not result.valid
    assert any(i.code == "export_formats_empty" for i in result.errors)


def test_validator_rejects_empty_checkpoint_template():
    model = PpoPlannerModel(
        projectName="demo",
        checkpoint=CheckpointConfig(filenameTemplate="  "),
    )
    result = PpoValidator(model).validate()
    assert not result.valid


def test_validator_warns_json_header_comments():
    model = PpoPlannerModel(
        projectName="demo",
        exportFormat=ExportFormatConfig(
            formats=[ExportConfigFormat.JSON, ExportConfigFormat.JSON_MIN],
            includeHeaderComments=True,
        ),
    )
    result = PpoValidator(model).validate()
    assert any(i.code == "json_header_comments" for i in result.warnings)


def test_legacy_single_format_migrates_to_list():
    raw = {
        "projectName": "legacy",
        "params": {},
        "parallel": {"numEnvs": 1, "vecEnvType": "dummy", "nProc": None},
        "exportFormat": {"format": "json"},
    }
    model = PpoPlannerModel.model_validate(raw)
    assert model.exportFormat.formats == [ExportConfigFormat.JSON]


def test_legacy_model_gets_output_defaults():
    raw = {
        "projectName": "legacy",
        "params": {},
        "parallel": {"numEnvs": 1, "vecEnvType": "dummy", "nProc": None},
    }
    model = PpoPlannerModel.model_validate(raw)
    assert model.checkpoint.enabled is True
    assert model.bestModel.enabled is True
    assert model.exportFormat.formats == [ExportConfigFormat.YAML]
