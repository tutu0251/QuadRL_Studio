"""Canonical quadruped gait parameters."""
from __future__ import annotations

from domain.models import GaitPhaseOffsets, GaitType

_GAIT_SPECS: dict[str, dict] = {
    "stand": {
        "name": "Stand",
        "cycleTime": 1.0,
        "dutyFactor": 1.0,
        "phaseOffsets": (0.0, 0.0, 0.0, 0.0),
        "swingHeight": 0.0,
        "stepLength": 0.0,
        "bodyHeight": 0.35,
    },
    "recover": {
        "name": "Recover",
        "cycleTime": 0.8,
        "dutyFactor": 0.85,
        "phaseOffsets": (0.0, 0.25, 0.5, 0.75),
        "swingHeight": 0.04,
        "stepLength": 0.05,
        "bodyHeight": 0.35,
    },
    "walk": {
        "name": "Walk",
        "cycleTime": 0.6,
        "dutyFactor": 0.75,
        "phaseOffsets": (0.0, 0.25, 0.5, 0.75),
        "swingHeight": 0.06,
        "stepLength": 0.12,
        "bodyHeight": 0.35,
    },
    "trot": {
        "name": "Trot",
        "cycleTime": 0.45,
        "dutyFactor": 0.5,
        "phaseOffsets": (0.0, 0.5, 0.5, 0.0),
        "swingHeight": 0.08,
        "stepLength": 0.18,
        "bodyHeight": 0.35,
    },
    "pace": {
        "name": "Pace / Lateral trot",
        "cycleTime": 0.42,
        "dutyFactor": 0.5,
        "phaseOffsets": (0.0, 0.0, 0.5, 0.5),
        "swingHeight": 0.08,
        "stepLength": 0.16,
        "bodyHeight": 0.35,
    },
    "bound": {
        "name": "Bound",
        "cycleTime": 0.35,
        "dutyFactor": 0.45,
        "phaseOffsets": (0.0, 0.0, 0.5, 0.5),
        "swingHeight": 0.1,
        "stepLength": 0.25,
        "bodyHeight": 0.34,
    },
    "gallop": {
        "name": "Gallop",
        "cycleTime": 0.28,
        "dutyFactor": 0.4,
        "phaseOffsets": (0.0, 0.15, 0.45, 0.6),
        "swingHeight": 0.12,
        "stepLength": 0.35,
        "bodyHeight": 0.33,
    },
}


def _offsets(t: tuple[float, float, float, float]) -> GaitPhaseOffsets:
    return GaitPhaseOffsets(fl=t[0], fr=t[1], rl=t[2], rr=t[3])


def build_gait(gait_id: str) -> GaitType:
    spec = _GAIT_SPECS.get(gait_id)
    if not spec:
        raise KeyError(f"Unknown gait: {gait_id}")
    return GaitType(
        id=gait_id,
        name=spec["name"],
        builtin=True,
        cycleTime=spec["cycleTime"],
        dutyFactor=spec["dutyFactor"],
        phaseOffsets=_offsets(spec["phaseOffsets"]),
        swingHeight=spec["swingHeight"],
        stepLength=spec["stepLength"],
        bodyHeight=spec["bodyHeight"],
    )


def default_gait_library() -> list[GaitType]:
    return [build_gait(gid) for gid in _GAIT_SPECS]


def list_gait_catalog() -> list[dict]:
    return [{"id": gid, "name": _GAIT_SPECS[gid]["name"]} for gid in _GAIT_SPECS]
