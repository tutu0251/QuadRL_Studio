"""Recommended observation normalization — env applies (raw - offset) / scale then clip."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import ObservationTerm


@dataclass(frozen=True)
class NormDefaults:
    scale: float
    offset: float = 0.0
    clip_min: float | None = -1.0
    clip_max: float | None = 1.0


PROCEDURAL_NORM: dict[str, NormDefaults] = {
    "joint_positions": NormDefaults(scale=2.0),
    "joint_velocities": NormDefaults(scale=6.0),
    "last_actions": NormDefaults(scale=1.0),
    "commands": NormDefaults(scale=1.0),
    "base_lin_vel": NormDefaults(scale=2.0),
    "base_ang_vel": NormDefaults(scale=8.0),
    "projected_gravity": NormDefaults(scale=1.0, clip_min=None, clip_max=None),
}

SENSOR_KIND_NORM: dict[str, NormDefaults] = {
    "imu": NormDefaults(scale=5.0),
    "contact": NormDefaults(scale=1.0, clip_min=0.0, clip_max=1.0),
    "odom": NormDefaults(scale=2.0),
    "lidar": NormDefaults(scale=30.0, clip_min=0.0, clip_max=1.0),
}

DEFAULT_NORM = NormDefaults(scale=1.0)


def recommended_normalization(term: ObservationTerm) -> NormDefaults:
    if term.source == "procedural" and term.id in PROCEDURAL_NORM:
        return PROCEDURAL_NORM[term.id]
    kind = term.kind.lower()
    if kind in SENSOR_KIND_NORM:
        return SENSOR_KIND_NORM[kind]
    return DEFAULT_NORM


def apply_recommended_normalization(term: ObservationTerm) -> ObservationTerm:
    d = recommended_normalization(term)
    term.scale = d.scale
    term.offset = d.offset
    term.clipMin = d.clip_min
    term.clipMax = d.clip_max
    return term
