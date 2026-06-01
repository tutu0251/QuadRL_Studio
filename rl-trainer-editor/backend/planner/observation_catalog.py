"""Observation catalog — procedural groups + sensor instances from the project."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from domain.models import ObservationTerm
from planner.observation_normalization import apply_recommended_normalization
from storage import project_storage

ObservationSource = Literal["procedural", "sensor"]


@dataclass(frozen=True)
class ProceduralCatalogEntry:
    id: str
    label: str
    kind: str
    category: str
    description: str


PROCEDURAL_CATALOG: tuple[ProceduralCatalogEntry, ...] = (
    ProceduralCatalogEntry(
        "joint_positions",
        "Joint positions",
        "joint_state",
        "state",
        "Relative joint positions from the sim / ros2_control state.",
    ),
    ProceduralCatalogEntry(
        "joint_velocities",
        "Joint velocities",
        "joint_state",
        "state",
        "Joint velocities from the sim / ros2_control state.",
    ),
    ProceduralCatalogEntry(
        "last_actions",
        "Last actions",
        "action",
        "state",
        "Previous policy action vector (action history for smoothness).",
    ),
    ProceduralCatalogEntry(
        "commands",
        "Commands",
        "command",
        "command",
        "Target velocity, height, and gait command from the task.",
    ),
    ProceduralCatalogEntry(
        "base_lin_vel",
        "Base linear velocity",
        "base_state",
        "state",
        "Base linear velocity in body frame (odom or kinematics).",
    ),
    ProceduralCatalogEntry(
        "base_ang_vel",
        "Base angular velocity",
        "base_state",
        "state",
        "Base angular velocity (IMU or kinematics).",
    ),
    ProceduralCatalogEntry(
        "projected_gravity",
        "Projected gravity",
        "orientation",
        "state",
        "Gravity vector in body frame (IMU orientation or equivalent).",
    ),
)

_CATEGORY_SENSOR_KINDS: dict[str, set[str]] = {
    "contact": {"contact"},
    "orientation": {"imu"},
    "posture": {"imu"},
    "gait": {"contact"},
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def _observation_key(name: str) -> str:
    return name.replace("-", "_").replace(" ", "_")


def _fields_for_sensor(kind: str, sensor: dict[str, Any]) -> list[str]:
    if kind == "imu":
        fields = ["angular_velocity", "linear_acceleration"]
        imu = sensor.get("imu") or {}
        if imu.get("enableOrientation"):
            fields.append("orientation")
        return fields
    if kind == "contact":
        return ["contacts"]
    if kind == "odom":
        odom = sensor.get("odom") or {}
        dims = odom.get("dimensions", 3)
        if dims == 2:
            return ["linear_velocity_x", "angular_velocity_z"]
        return ["linear_velocity_x", "linear_velocity_y", "angular_velocity_z"]
    if kind == "lidar":
        return ["ranges", "angle_min", "angle_max"]
    return []


def _load_sensor_model(name: str) -> dict[str, Any] | None:
    path = project_storage.sensor_model_path(name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _sensor_terms_from_model(project: str) -> list[ObservationTerm]:
    doc = _load_sensor_model(project)
    if not doc:
        return _sensor_terms_from_yaml(project)

    sensors = doc.get("sensors") or []
    if not isinstance(sensors, list):
        return []

    terms: list[ObservationTerm] = []
    for sensor in sensors:
        if not isinstance(sensor, dict):
            continue
        sensor_id = str(sensor.get("id") or "")
        kind = str(sensor.get("kind") or "").lower()
        name = str(sensor.get("name") or sensor_id or kind)
        key = _observation_key(name)
        terms.append(
            ObservationTerm(
                id=f"sensor:{sensor_id or key}",
                source="sensor",
                kind=kind,
                category="sensor",
                label=name,
                enabled=False,
                available=bool(sensor.get("enabled", True)),
                key=key,
                topic=str(sensor.get("rosTopic") or ""),
                parentLink=str(sensor.get("parentLink") or ""),
                rateHz=float(sensor.get("updateRate") or 0),
                fields=_fields_for_sensor(kind, sensor),
                sensorId=sensor_id,
            )
        )
    return terms


def _sensor_terms_from_yaml(project: str) -> list[ObservationTerm]:
    doc = project_storage.load_observations_doc(project)
    if not doc:
        return []
    obs = doc.get("observations") or {}
    if not isinstance(obs, dict):
        return []

    terms: list[ObservationTerm] = []
    for key, spec in obs.items():
        if not isinstance(spec, dict):
            continue
        kind = str(spec.get("kind") or "").lower()
        terms.append(
            ObservationTerm(
                id=f"sensor:{key}",
                source="sensor",
                kind=kind,
                category="sensor",
                label=key,
                enabled=False,
                available=True,
                key=key,
                topic=str(spec.get("topic") or ""),
                msgType=str(spec.get("msg_type") or ""),
                parentLink=str(spec.get("parent_link") or ""),
                rateHz=float(spec.get("rate_hz") or 0),
                fields=list(spec.get("fields") or []),
                sensorId=key,
            )
        )
    return terms


def build_observation_catalog(project: str) -> list[ObservationTerm]:
    """Full catalog: procedural entries + all sensor instances for the project."""
    terms: list[ObservationTerm] = []
    for entry in PROCEDURAL_CATALOG:
        terms.append(
            ObservationTerm(
                id=entry.id,
                source="procedural",
                kind=entry.kind,
                category=entry.category,
                label=entry.label,
                enabled=False,
                available=True,
                key=entry.id,
                description=entry.description,
            )
        )
    terms = [apply_recommended_normalization(t) for t in terms]
    terms.extend(_sensor_terms_from_model(project))
    return [apply_recommended_normalization(t) for t in terms]


def merge_observation_terms(
    existing: list[ObservationTerm] | None,
    project: str,
) -> list[ObservationTerm]:
    """Merge saved selection with the latest project catalog."""
    catalog = build_observation_catalog(project)
    by_id = {t.id: t.model_copy(deep=True) for t in (existing or [])}
    merged: list[ObservationTerm] = []
    for cat in catalog:
        prev = by_id.get(cat.id)
        if prev:
            term = cat.model_copy(deep=True)
            term.enabled = prev.enabled if prev.available or cat.available else False
            term.scale = prev.scale if prev.scale > 0 else cat.scale
            term.offset = prev.offset
            term.clipMin = prev.clipMin
            term.clipMax = prev.clipMax
            if prev.label and cat.source == "sensor":
                term.label = prev.label
            merged.append(term)
        else:
            merged.append(cat)
    return merged


def recommend_observation_terms(
    terms: list[ObservationTerm],
    *,
    reward_categories: set[str],
) -> tuple[list[ObservationTerm], list[str]]:
    """Enable a recommended subset based on enabled reward categories."""
    needs_contact = bool({"contact", "gait"} & reward_categories)
    needs_imu = bool({"orientation", "posture"} & reward_categories)
    needs_velocity = bool({"velocity", "tracking"} & reward_categories)
    needs_action = bool({"action_smoothness"} & reward_categories)

    core_procedural = {
        "joint_positions",
        "joint_velocities",
        "last_actions",
        "commands",
    }
    velocity_procedural = {"base_lin_vel", "base_ang_vel"}
    orientation_procedural = {"projected_gravity"}

    out: list[ObservationTerm] = []
    notes: list[str] = []

    for term in terms:
        t = term.model_copy(deep=True)
        if not t.available:
            t.enabled = False
            out.append(t)
            continue

        if t.source == "procedural":
            enable = t.id in core_procedural
            if needs_velocity and t.id in velocity_procedural:
                enable = True
            if needs_imu and t.id in orientation_procedural:
                enable = True
            if needs_action and t.id == "last_actions":
                enable = True
            t.enabled = enable
        else:
            kind = t.kind.lower()
            enable = False
            if kind == "contact" and needs_contact:
                enable = True
            elif kind == "imu" and needs_imu:
                enable = True
            elif kind == "odom" and needs_velocity:
                enable = True
            elif kind == "lidar":
                enable = False
            t.enabled = enable
        out.append(t)

    enabled_count = sum(1 for t in out if t.enabled)
    out = [apply_recommended_normalization(t) for t in out]
    notes.append(
        f"Recommended {enabled_count} of {len(out)} observations "
        f"for reward categories: {sorted(reward_categories) or ['default']}."
    )
    return out, notes
