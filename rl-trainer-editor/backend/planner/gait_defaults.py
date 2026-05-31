"""Canonical quadruped gate-type parameters."""
from __future__ import annotations

from domain.models import GaitPhaseOffsets, GaitType

_GAIT_CATALOG = ("none", "walk", "trot", "gallop")

# Legacy stage / project IDs map to catalog entries for recommend & migration.
_GAIT_ALIASES: dict[str, str] = {
    "stand": "none",
    "recover": "none",
    "pace": "trot",
    "bound": "gallop",
}

_GAIT_SPECS: dict[str, dict] = {
    "none": {
        "name": "None",
        "cycleTime": 1.0,
        "dutyFactor": 1.0,
        "phaseOffsets": (0.0, 0.0, 0.0, 0.0),
        "swingHeight": 0.0,
        "stepLength": 0.0,
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


def resolve_gait_id(gait_id: str) -> str:
    return _GAIT_ALIASES.get(gait_id, gait_id)


def _offsets(t: tuple[float, float, float, float]) -> GaitPhaseOffsets:
    return GaitPhaseOffsets(fl=t[0], fr=t[1], rl=t[2], rr=t[3])


def build_gait(gait_id: str) -> GaitType:
    canonical = resolve_gait_id(gait_id)
    spec = _GAIT_SPECS.get(canonical)
    if not spec:
        raise KeyError(f"Unknown gait: {gait_id}")
    return GaitType(
        id=canonical,
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
    return [build_gait(gid) for gid in _GAIT_CATALOG]


def list_gait_catalog() -> list[dict]:
    return [{"id": gid, "name": _GAIT_SPECS[gid]["name"]} for gid in _GAIT_CATALOG]
