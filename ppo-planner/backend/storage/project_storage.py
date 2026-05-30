"""Project storage — ppo_model.json and training export YAML."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from domain.models import PpoPlannerModel

PROJECTS_ROOT = Path.home() / "quadruped_dev_tool" / "projects"
PPO_FILE = "ppo_model.json"
SENSOR_FILE = "sensor_model.json"
EXPORTS_DIR = "exports"
PPO_PREFIX = "ppo_"


def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def ppo_model_path(name: str) -> Path:
    return project_dir(name) / PPO_FILE


def export_ppo_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{PPO_PREFIX}{name}_config.yaml"


def sensor_model_path(name: str) -> Path:
    return project_dir(name) / SENSOR_FILE


def ensure_project_dirs(name: str) -> Path:
    root = project_dir(name)
    (root / EXPORTS_DIR).mkdir(parents=True, exist_ok=True)
    return root


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    out: set[str] = set()
    for p in PROJECTS_ROOT.iterdir():
        if p.is_dir() and not p.name.startswith("."):
            out.add(p.name)
    return sorted(out)


def save_ppo(name: str, model: PpoPlannerModel) -> Path:
    root = ensure_project_dirs(name)
    path = root / PPO_FILE
    path.write_text(model.model_dump_json(indent=2))
    return path


def load_ppo(name: str) -> PpoPlannerModel:
    path = ppo_model_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No PPO model for project: {name}")
    return PpoPlannerModel.model_validate_json(path.read_text())


def has_ppo(name: str) -> bool:
    return ppo_model_path(name).exists()


def has_sensor_pipeline(name: str) -> bool:
    return sensor_model_path(name).exists()


def load_robot_name(name: str) -> Optional[str]:
    path = sensor_model_path(name)
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("robotName")
    return None
