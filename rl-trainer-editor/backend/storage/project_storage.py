"""Project storage — rl_trainer_model.json and training export YAML."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from domain.models import RlTrainerModel

PROJECTS_ROOT = Path.home() / "quadruped_dev_tool" / "projects"
TRAINER_FILE = "rl_trainer_model.json"
SENSOR_FILE = "sensor_model.json"
EXPORTS_DIR = "exports"
RL_PREFIX = "rl_"
PPO_PREFIX = "ppo_"
SENS_PREFIX = "sens_"
CTRL_PREFIX = "ctrl_"


def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def trainer_model_path(name: str) -> Path:
    return project_dir(name) / TRAINER_FILE


def export_rl_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{RL_PREFIX}{name}_config.yaml"


def export_ppo_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{PPO_PREFIX}{name}_config.yaml"


def ppo_config_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{PPO_PREFIX}{name}_config.yaml"


def observations_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{SENS_PREFIX}{name}_observations.yaml"


def gains_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{CTRL_PREFIX}{name}_gains.yaml"


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


def save_trainer(name: str, model: RlTrainerModel) -> Path:
    root = ensure_project_dirs(name)
    path = root / TRAINER_FILE
    path.write_text(model.model_dump_json(indent=2))
    return path


def load_trainer(name: str) -> RlTrainerModel:
    path = trainer_model_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No RL trainer model for project: {name}")
    from domain.migration import migrate_model

    model = RlTrainerModel.model_validate_json(path.read_text())
    return migrate_model(model)


def has_trainer(name: str) -> bool:
    return trainer_model_path(name).exists()


def has_sensor_pipeline(name: str) -> bool:
    return sensor_model_path(name).exists()


def load_robot_name(name: str) -> Optional[str]:
    path = sensor_model_path(name)
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("robotName")
    return None


def load_observations_keys(name: str) -> list[str]:
    doc = load_observations_doc(name)
    if not doc:
        return []
    obs = doc.get("observations") or {}
    return list(obs.keys()) if isinstance(obs, dict) else []


def load_observation_kinds(name: str) -> set[str]:
    doc = load_observations_doc(name)
    if not doc:
        return set()
    obs = doc.get("observations") or {}
    kinds: set[str] = set()
    if isinstance(obs, dict):
        for entry in obs.values():
            if isinstance(entry, dict) and entry.get("kind"):
                kinds.add(str(entry["kind"]).lower())
    return kinds


def load_observations_doc(name: str) -> Optional[dict[str, Any]]:
    path = observations_yaml_path(name)
    if not path.exists():
        return None
    try:
        doc = yaml.safe_load(path.read_text()) or {}
        return doc if isinstance(doc, dict) else None
    except (yaml.YAMLError, OSError):
        return None


def checkpoint_dir(name: str, directory: str = "checkpoints") -> Path:
    return project_dir(name) / directory


def list_checkpoints(name: str, directory: str = "checkpoints") -> list:
    from domain.models import CheckpointInfo

    ckpt_dir = checkpoint_dir(name, directory)
    if not ckpt_dir.is_dir():
        return []
    out: list[CheckpointInfo] = []
    for p in sorted(ckpt_dir.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = p.stat()
        rel = str(p.relative_to(project_dir(name)))
        out.append(
            CheckpointInfo(
                path=rel,
                filename=p.name,
                sizeBytes=stat.st_size,
                modifiedAt=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )
    return out
