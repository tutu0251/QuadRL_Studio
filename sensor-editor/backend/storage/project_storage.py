"""Project storage — imports ctrl_ URDF, exports sens_ RL artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from domain.models import SensorModel

PROJECTS_ROOT = Path.home() / "quadruped_dev_tool" / "projects"
SENSOR_FILE = "sensor_model.json"
CONTROL_FILE = "control_model.json"
EXPORTS_DIR = "exports"
CTRL_PREFIX = "ctrl_"
SENS_PREFIX = "sens_"


def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def ctrl_urdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{CTRL_PREFIX}{name}_ros2_control.urdf"


def ctrl_controllers_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{CTRL_PREFIX}{name}_controllers.yaml"


def ctrl_gains_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{CTRL_PREFIX}{name}_gains.yaml"


def sensor_model_path(name: str) -> Path:
    return project_dir(name) / SENSOR_FILE


def control_model_path(name: str) -> Path:
    return project_dir(name) / CONTROL_FILE


def export_rl_urdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{SENS_PREFIX}{name}_rl.urdf"


def export_sdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{SENS_PREFIX}{name}.sdf"


def export_bridge_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{SENS_PREFIX}{name}_bridge.yaml"


def export_observations_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{SENS_PREFIX}{name}_observations.yaml"


def ensure_project_dirs(name: str) -> Path:
    root = project_dir(name)
    (root / EXPORTS_DIR).mkdir(parents=True, exist_ok=True)
    return root


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    out: set[str] = set()
    for p in PROJECTS_ROOT.iterdir():
        if not p.is_dir():
            continue
        if (
            (p / SENSOR_FILE).exists()
            or ctrl_urdf_path(p.name).exists()
            or (p / CONTROL_FILE).exists()
        ):
            out.add(p.name)
    return sorted(out)


def save_sensor(name: str, model: SensorModel) -> Path:
    root = ensure_project_dirs(name)
    path = root / SENSOR_FILE
    path.write_text(model.model_dump_json(indent=2))
    return path


def load_sensor(name: str) -> SensorModel:
    path = sensor_model_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No sensor model for project: {name}. Import ctrl URDF first.")
    return SensorModel.model_validate_json(path.read_text())


def has_sensor(name: str) -> bool:
    return sensor_model_path(name).exists()


def has_ctrl_urdf(name: str) -> bool:
    return ctrl_urdf_path(name).is_file()


def load_control_robot_name(name: str) -> Optional[str]:
    path = control_model_path(name)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data.get("robotName")


def load_control_child_links(name: str) -> list[str]:
    """Return child link names from actuated joints in control_model.json."""
    path = control_model_path(name)
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    links: list[str] = []
    for j in data.get("actuatedJoints") or []:
        child = j.get("childLinkName") or ""
        if child and child not in links:
            links.append(child)
    return links
