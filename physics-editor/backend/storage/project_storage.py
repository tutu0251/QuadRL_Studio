"""Project storage — imports geo_ URDF, exports phy_ URDF/SDF."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from domain.models import RobotModel

PROJECTS_ROOT = Path.home() / "quadruped_dev_tool" / "projects"
PHYSICS_FILE = "physics_model.json"
EXPORTS_DIR = "exports"
GEO_PREFIX = "geo_"
PHY_PREFIX = "phy_"


def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def geo_urdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{GEO_PREFIX}{name}.urdf"


def export_urdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{PHY_PREFIX}{name}.urdf"


def export_sdf_path(name: str) -> Path:
    return project_dir(name) / EXPORTS_DIR / f"{PHY_PREFIX}{name}.sdf"


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
        if (p / PHYSICS_FILE).exists():
            out.add(p.name)
        elif geo_urdf_path(p.name).exists():
            out.add(p.name)
    return sorted(out)


def save_physics(name: str, model: RobotModel) -> Path:
    root = ensure_project_dirs(name)
    path = root / PHYSICS_FILE
    path.write_text(model.model_dump_json(indent=2))
    return path


def load_physics(name: str) -> RobotModel:
    path = project_dir(name) / PHYSICS_FILE
    if not path.exists():
        raise FileNotFoundError(f"No physics model for project: {name}. Import geo URDF first.")
    return RobotModel.model_validate_json(path.read_text())


def has_physics(name: str) -> bool:
    return (project_dir(name) / PHYSICS_FILE).exists()


def has_geo_urdf(name: str) -> bool:
    return geo_urdf_path(name).is_file()
