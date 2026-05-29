"""Persistent project storage on ~/quadruped_dev_tool/projects/."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from domain.models import RobotModel

PROJECTS_ROOT = Path.home() / "quadruped_dev_tool" / "projects"
ROBOT_FILE = "robot_model.json"
SNAPSHOTS_DIR = "snapshots"
EXPORTS_DIR = "exports"


def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def ensure_project_dirs(name: str) -> Path:
    root = project_dir(name)
    (root / SNAPSHOTS_DIR).mkdir(parents=True, exist_ok=True)
    (root / EXPORTS_DIR).mkdir(parents=True, exist_ok=True)
    return root


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(
        p.name for p in PROJECTS_ROOT.iterdir()
        if p.is_dir() and (p / ROBOT_FILE).exists()
    )


def save_robot(name: str, model: RobotModel) -> Path:
    root = ensure_project_dirs(name)
    path = root / ROBOT_FILE
    path.write_text(model.model_dump_json(indent=2))
    return path


def load_robot(name: str) -> RobotModel:
    path = project_dir(name) / ROBOT_FILE
    if not path.exists():
        raise FileNotFoundError(f"Project not found: {name}")
    return RobotModel.model_validate_json(path.read_text())


def create_snapshot(name: str, model: RobotModel, label: Optional[str] = None) -> str:
    root = ensure_project_dirs(name)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snap_id = label or f"snapshot_{ts}"
    snap_path = root / SNAPSHOTS_DIR / f"{snap_id}.json"
    meta = {"id": snap_id, "created": datetime.now(timezone.utc).isoformat(), "model": model.model_dump()}
    snap_path.write_text(json.dumps(meta, indent=2))
    return snap_id


def list_snapshots(name: str) -> list[dict]:
    snap_dir = project_dir(name) / SNAPSHOTS_DIR
    if not snap_dir.exists():
        return []
    out = []
    for f in sorted(snap_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            out.append({"id": data.get("id", f.stem), "created": data.get("created"), "file": f.name})
        except json.JSONDecodeError:
            out.append({"id": f.stem, "created": None, "file": f.name})
    return out


def restore_snapshot(name: str, snap_id: str) -> RobotModel:
    snap_path = project_dir(name) / SNAPSHOTS_DIR / f"{snap_id}.json"
    if not snap_path.exists():
        matches = list((project_dir(name) / SNAPSHOTS_DIR).glob(f"{snap_id}*"))
        if not matches:
            raise FileNotFoundError(f"Snapshot not found: {snap_id}")
        snap_path = matches[0]
    data = json.loads(snap_path.read_text())
    return RobotModel.model_validate(data["model"])


def export_path(name: str, filename: str) -> Path:
    root = ensure_project_dirs(name)
    return root / EXPORTS_DIR / filename
