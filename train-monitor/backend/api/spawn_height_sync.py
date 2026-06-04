"""Recalculate grounded spawn Z and sync related training height parameters."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from api.spawn_grounding import compute_grounded_spawn_z
from storage import monitor_storage, project_storage

_GEO_BACKEND = Path(__file__).resolve().parents[3] / "geometry-editor" / "backend"


def _import_standing_height_params():
    tm_backend = str(Path(__file__).resolve().parent.parent)
    geo_backend = str(_GEO_BACKEND)
    removed_tm = tm_backend in sys.path
    if removed_tm:
        sys.path.remove(tm_backend)
    sys.path.insert(0, geo_backend)
    purged: list[str] = []
    try:
        for key in list(sys.modules):
            mod = sys.modules.get(key)
            mod_file = getattr(mod, "__file__", "") or ""
            if key == "domain" or key.startswith("domain."):
                if "geometry-editor" in mod_file or key in (
                    "domain",
                    "domain.models",
                    "domain.pose_utils",
                    "domain.standing_heights",
                ):
                    purged.append(key)
                    del sys.modules[key]
        from domain.standing_heights import (  # noqa: WPS433
            assert_height_policy_consistent,
            standing_height_params,
        )

        return standing_height_params, assert_height_policy_consistent
    finally:
        if geo_backend in sys.path:
            sys.path.remove(geo_backend)
        if removed_tm:
            sys.path.insert(0, tm_backend)
        for key in purged:
            sys.modules.pop(key, None)


def _spawn_z_from_geometry_model(project: str) -> float | None:
    model_path = project_storage.project_dir(project) / "robot_model.json"
    if not model_path.is_file():
        return None

    tm_backend = str(Path(__file__).resolve().parent.parent)
    geo_backend = str(_GEO_BACKEND)
    removed_tm = tm_backend in sys.path
    if removed_tm:
        sys.path.remove(tm_backend)
    sys.path.insert(0, geo_backend)
    purged: list[str] = []
    try:
        for key in list(sys.modules):
            mod = sys.modules.get(key)
            mod_file = getattr(mod, "__file__", "") or ""
            if key == "domain" or key.startswith("domain."):
                if "geometry-editor" in mod_file or key in (
                    "domain",
                    "domain.models",
                    "domain.pose_utils",
                ):
                    purged.append(key)
                    del sys.modules[key]
        from domain.models import RobotModel  # noqa: WPS433
        from domain.pose_utils import (  # noqa: WPS433
            apply_pose_to_joints,
            compute_grounded_spawn_z_for_model,
            get_default_pose,
        )

        model = RobotModel.model_validate(json.loads(model_path.read_text(encoding="utf-8")))
        pose = get_default_pose(model)
        if pose:
            apply_pose_to_joints(model, pose.id)
        return float(compute_grounded_spawn_z_for_model(model))
    finally:
        if geo_backend in sys.path:
            sys.path.remove(geo_backend)
        if removed_tm:
            sys.path.insert(0, tm_backend)
        for key in purged:
            sys.modules.pop(key, None)


def _load_yaml(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        return {}, ""
    raw = path.read_text(encoding="utf-8")
    header_lines = [line for line in raw.splitlines() if line.strip().startswith("#")]
    header = "\n".join(header_lines)
    if header:
        header += "\n"
    body = "\n".join(line for line in raw.splitlines() if not line.strip().startswith("#"))
    doc = yaml.safe_load(body) or {}
    return (doc if isinstance(doc, dict) else {}), header


def _save_yaml(path: Path, doc: dict[str, Any], header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + yaml.dump(doc, default_flow_style=False, sort_keys=False), encoding="utf-8")


def _patch_height_fields(
    obj: Any,
    *,
    target: float,
    fall_h: float,
    spawn_z: float,
) -> None:
    if isinstance(obj, dict):
        for key, val in list(obj.items()):
            if key == "target_body_height":
                obj[key] = target
            elif key == "target_height":
                obj[key] = target
            elif key == "body_height":
                obj[key] = target
            elif key == "fall_base_height_threshold":
                obj[key] = fall_h
            elif key == "spawn" and isinstance(val, dict) and "z" in val:
                val["z"] = spawn_z
            else:
                _patch_height_fields(obj[key], target=target, fall_h=fall_h, spawn_z=spawn_z)
    elif isinstance(obj, list):
        for item in obj:
            _patch_height_fields(item, target=target, fall_h=fall_h, spawn_z=spawn_z)


def recalculate_spawn_and_training_heights(project: str) -> dict[str, float | str]:
    """Ground feet on z=0; align spawn, target_body_height, and fall threshold."""
    name = project.strip()
    urdf = project_storage.project_dir(name) / "exports" / f"geo_{name}.urdf"
    if not urdf.is_file():
        raise FileNotFoundError(f"Missing geometry URDF: {urdf}")

    standing_height_params, assert_height_policy_consistent = _import_standing_height_params()

    pose_doc = monitor_storage.load_pose_doc(name)
    joints = {str(k): float(v) for k, v in (pose_doc.get("joints") or {}).items()}
    grounded_z = _spawn_z_from_geometry_model(name)
    if grounded_z is None:
        grounded_z = float(compute_grounded_spawn_z(urdf, joints or None))
    heights = standing_height_params(grounded_z)

    spawn_block = {
        "x": 0.0,
        "y": 0.0,
        "z": heights.spawn_z,
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": 0.0,
    }
    pose_doc["spawn"] = dict(spawn_block)
    pose_doc["_base_spawn"] = dict(spawn_block)
    pose_doc["height_policy"] = heights.as_metadata()
    if "spawn_offset" not in pose_doc:
        pose_doc["spawn_offset"] = {
            "dx": 0.0,
            "dy": 0.0,
            "dz": 0.0,
            "droll": 0.0,
            "dpitch": 0.0,
            "dyaw": 0.0,
        }
    monitor_storage.save_pose_doc(name, pose_doc)

    rl_path = project_storage.rl_config_path(name)
    rl_doc, rl_header = _load_yaml(rl_path)
    if rl_doc:
        _patch_height_fields(
            rl_doc,
            target=heights.target_body_height,
            fall_h=heights.fall_base_height_threshold,
            spawn_z=heights.spawn_z,
        )
        _save_yaml(rl_path, rl_doc, rl_header)

    trainer_json = project_storage.project_dir(name) / "rl_trainer_model.json"
    if trainer_json.is_file():
        text = trainer_json.read_text(encoding="utf-8")
        text = re.sub(
            r'"targetBodyHeight"\s*:\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',
            f'"targetBodyHeight": {heights.target_body_height}',
            text,
        )
        text = re.sub(
            r'"bodyHeight"\s*:\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',
            f'"bodyHeight": {heights.target_body_height}',
            text,
        )
        text = re.sub(
            r'"fallBaseHeightThreshold"\s*:\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',
            f'"fallBaseHeightThreshold": {heights.fall_base_height_threshold}',
            text,
        )
        trainer_json.write_text(text, encoding="utf-8")

    assert_height_policy_consistent(heights)
    return heights.as_metadata()
