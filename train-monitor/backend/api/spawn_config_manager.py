"""Spawn pose / offset / controller delay configuration."""
from __future__ import annotations

from typing import Any

from api.command_builder import build_spawn_patch_command
from domain.models import SpawnConfig, SpawnConfigUpdate, SpawnOffset
from storage import monitor_storage, project_storage


def _spawn_keys() -> tuple[str, ...]:
    return ("x", "y", "z", "roll", "pitch", "yaw")


def _offset_from_doc(doc: dict[str, Any]) -> SpawnOffset:
    raw = doc.get("spawn_offset") or {}
    return SpawnOffset(
        dx=float(raw.get("dx", 0.0)),
        dy=float(raw.get("dy", 0.0)),
        dz=float(raw.get("dz", 0.0)),
        droll=float(raw.get("droll", 0.0)),
        dpitch=float(raw.get("dpitch", 0.0)),
        dyaw=float(raw.get("dyaw", 0.0)),
    )


def _timing_from_doc(doc: dict[str, Any]) -> tuple[float, bool]:
    timing = doc.get("timing") or {}
    delay = float(timing.get("controller_apply_delay_s", monitor_storage.DEFAULT_CONTROLLER_DELAY_S))
    confirmed = bool(timing.get("pose_confirmed", False))
    return delay, confirmed


def _spawn_dict(raw: dict[str, Any] | None) -> dict[str, float]:
    base = raw or {}
    return {k: float(base.get(k, 0.0)) for k in _spawn_keys()}


def _effective_spawn(base: dict[str, float], offset: SpawnOffset) -> dict[str, float]:
    return {
        "x": base["x"] + offset.dx,
        "y": base["y"] + offset.dy,
        "z": base["z"] + offset.dz,
        "roll": base["roll"] + offset.droll,
        "pitch": base["pitch"] + offset.dpitch,
        "yaw": base["yaw"] + offset.dyaw,
    }


def _base_spawn_from_doc(doc: dict[str, Any], offset: SpawnOffset) -> dict[str, float]:
    stored = doc.get("_base_spawn")
    if isinstance(stored, dict):
        return _spawn_dict(stored)
    effective = _spawn_dict(doc.get("spawn"))
    return {
        "x": effective["x"] - offset.dx,
        "y": effective["y"] - offset.dy,
        "z": effective["z"] - offset.dz,
        "roll": effective["roll"] - offset.droll,
        "pitch": effective["pitch"] - offset.dpitch,
        "yaw": effective["yaw"] - offset.dyaw,
    }


def get_spawn_config(name: str) -> SpawnConfig:
    path = monitor_storage.geo_spawn_export_path(name)
    doc = monitor_storage.load_pose_doc(name)
    offset = _offset_from_doc(doc)
    base_spawn = _base_spawn_from_doc(doc, offset)
    effective = _effective_spawn(base_spawn, offset)
    delay, confirmed = _timing_from_doc(doc)
    joints = doc.get("joints") or {}

    rel = f"exports/geo_{name}_default_pose.yaml"
    if path.is_file():
        rel = str(path.relative_to(project_storage.project_dir(name)))

    return SpawnConfig(
        project=name,
        export_path=rel,
        pose_name=str(doc.get("name", "Default Stand")),
        base_spawn=base_spawn,
        spawn_offset=offset,
        effective_spawn=effective,
        joints={str(k): float(v) for k, v in joints.items()},
        controller_apply_delay_s=delay,
        pose_confirmed=confirmed,
        missing_export=not path.is_file(),
    )


def update_spawn_config(name: str, update: SpawnConfigUpdate) -> tuple[SpawnConfig, str]:
    doc = monitor_storage.load_pose_doc(name)
    if not doc:
        doc = {
            "name": "Default Stand",
            "spawn": {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            "joints": {},
        }

    offset = _offset_from_doc(doc)
    base_spawn = _base_spawn_from_doc(doc, offset)
    timing = dict(doc.get("timing") or {})

    if update.spawn_offset is not None:
        o = update.spawn_offset
        offset = o
        doc["spawn_offset"] = {
            "dx": o.dx,
            "dy": o.dy,
            "dz": o.dz,
            "droll": o.droll,
            "dpitch": o.dpitch,
            "dyaw": o.dyaw,
        }

    if update.controller_apply_delay_s is not None:
        timing["controller_apply_delay_s"] = float(update.controller_apply_delay_s)

    if update.pose_confirmed is not None:
        timing["pose_confirmed"] = bool(update.pose_confirmed)

    doc["_base_spawn"] = base_spawn
    doc["spawn"] = _effective_spawn(base_spawn, offset)
    doc["timing"] = timing
    monitor_storage.save_pose_doc(name, doc)

    cfg = get_spawn_config(name)
    body = update.model_dump(exclude_none=True)
    command = build_spawn_patch_command(name, body)
    return cfg, command


def controller_apply_delay_for_project(name: str) -> float:
    doc = monitor_storage.load_pose_doc(name)
    timing = doc.get("timing") or {}
    return float(timing.get("controller_apply_delay_s", monitor_storage.DEFAULT_CONTROLLER_DELAY_S))


def resolve_spawn_create_pose(cfg: SpawnConfig) -> dict[str, float]:
    """Effective 6-DOF spawn pose (geometry export base + offset), same as training reset."""
    s = cfg.effective_spawn
    return {
        "x": float(s.get("x", 0.0)),
        "y": float(s.get("y", 0.0)),
        "z": float(s.get("z", 0.0)),
        "roll": float(s.get("roll", 0.0)),
        "pitch": float(s.get("pitch", 0.0)),
        "yaw": float(s.get("yaw", 0.0)),
    }


def initial_model_create_pose() -> dict[str, float]:
    """Neutral placement for ros_gz_sim create; pose is applied via SetEntityPose after."""
    return {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0}
