"""Project storage — imports phy_ URDF, exports ctrl_ ros2_control artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from domain.models import ControlModel, normalize_gazebo_plugin, normalize_sim_controller

PROJECTS_ROOT = Path.home() / "quadruped_dev_tool" / "projects"
CONTROL_FILE = "control_model.json"
PHYSICS_FILE = "physics_model.json"
EXPORTS_DIR = "exports"
PHY_PREFIX = "phy_"
GEO_PREFIX = "geo_"
CTRL_PREFIX = "ctrl_"


def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def phy_urdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{PHY_PREFIX}{name}.urdf"


def physics_model_path(name: str) -> Path:
    return project_dir(name) / PHYSICS_FILE


def control_model_path(name: str) -> Path:
    return project_dir(name) / CONTROL_FILE


def export_ros2_urdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{CTRL_PREFIX}{name}_ros2_control.urdf"


def export_controllers_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{CTRL_PREFIX}{name}_controllers.yaml"


def export_gains_yaml_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{CTRL_PREFIX}{name}_gains.yaml"


def geo_spawn_export_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{GEO_PREFIX}{name}_default_pose.yaml"


def load_geo_spawn_export_joints(name: str) -> dict[str, float]:
    path = geo_spawn_export_path(name)
    if not path.is_file():
        return {}
    import yaml

    text = path.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    doc = yaml.safe_load(body) or {}
    joints = doc.get("joints") or {}
    return {str(k): float(v) for k, v in joints.items()}


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
        if (p / CONTROL_FILE).exists() or phy_urdf_path(p.name).exists():
            out.add(p.name)
    return sorted(out)


def save_control(name: str, model: ControlModel) -> Path:
    root = ensure_project_dirs(name)
    path = root / CONTROL_FILE
    path.write_text(model.model_dump_json(indent=2))
    return path


def load_control(name: str) -> ControlModel:
    path = control_model_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No control model for project: {name}. Import phy URDF first.")
    model = ControlModel.model_validate_json(path.read_text())
    changed = normalize_sim_controller(model) or normalize_gazebo_plugin(model)
    if changed:
        save_control(name, model)
    return model


def has_control(name: str) -> bool:
    return control_model_path(name).exists()


def has_phy_urdf(name: str) -> bool:
    return phy_urdf_path(name).is_file()


def load_physics_joint_dynamics(name: str) -> dict[str, dict]:
    """Return joint name -> dynamics dict from physics_model.json if present."""
    path = physics_model_path(name)
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    out: dict[str, dict] = {}
    joints = data.get("joints") or []
    link_by_id = {l["id"]: l["name"] for l in data.get("links") or []}
    for j in joints:
        jname = j.get("name")
        if not jname:
            continue
        dyn = j.get("dynamics") or {}
        child_id = j.get("childLinkId")
        child_name = link_by_id.get(child_id, "")
        out[jname] = {
            "effort": dyn.get("effort", 100.0),
            "velocity": dyn.get("velocity", 10.0),
            "damping": dyn.get("damping", 0.0),
            "friction": dyn.get("friction", 0.0),
            "lowerLimit": j.get("lowerLimit", -3.14),
            "upperLimit": j.get("upperLimit", 3.14),
            "defaultValue": j.get("defaultValue", 0.0),
            "type": j.get("type", "revolute"),
            "childLinkName": child_name,
        }
    return out
