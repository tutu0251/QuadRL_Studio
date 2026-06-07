"""Pack ROS sensor readings into policy observation blocks (field-order contract)."""
from __future__ import annotations

from typing import Any

import numpy as np


def fit_dim(arr: np.ndarray | None, n: int) -> np.ndarray:
    """Pad or truncate a vector to exactly n floats."""
    out = np.zeros(max(n, 1), dtype=np.float32)
    if arr is None:
        return out
    flat = np.asarray(arr, dtype=np.float32).reshape(-1)
    if flat.size == 0:
        return out
    copy_len = min(int(flat.size), int(n))
    out[:copy_len] = flat[:copy_len]
    return out


def field_dim(kind: str, field: str) -> int:
    k = (kind or "").lower()
    if k == "contact":
        return 1
    if k == "odom":
        return 1
    if k == "lidar":
        return 16 if field == "ranges" else 1
    return 3


def sensor_term_dim(kind: str, fields: list[str]) -> int:
    k = (kind or "").lower()
    if k == "contact":
        return max(1, len(fields) or 1)
    if k == "lidar":
        return 16
    if k == "odom":
        return max(1, len(fields) or 1)
    if not fields:
        return 3
    return max(3, sum(field_dim(k, f) for f in fields))


def normalized_gravity(linear_accel: np.ndarray) -> np.ndarray:
    """Body-frame gravity *direction* from an accelerometer.

    An IMU at rest measures specific force (proper acceleration), which points
    *opposite* to gravity: a level robot reads ~(0, 0, +9.81) along body-up.
    Negate so the returned unit vector points the way gravity does — (0, 0, -1)
    when upright — matching the reset convention and ``SimState.tilt_rad``.
    Without this, a stationary upright robot reads (0, 0, +1), which tilt_rad
    interprets as fully upside-down (π rad) and terminates every episode on
    step 1 (reason=max_tilt).
    """
    g = np.asarray(linear_accel, dtype=np.float32).reshape(3)
    norm = float(np.linalg.norm(g))
    if norm > 1e-3:
        return (-g / norm).astype(np.float32)
    return np.array([0.0, 0.0, -1.0], dtype=np.float32)


def pack_imu(
    fields: list[str],
    *,
    angular_velocity: np.ndarray,
    linear_acceleration: np.ndarray,
    orientation: np.ndarray | None = None,
) -> np.ndarray:
    ang = np.asarray(angular_velocity, dtype=np.float32).reshape(3)
    lin = np.asarray(linear_acceleration, dtype=np.float32).reshape(3)
    orient = np.zeros(3, dtype=np.float32)
    if orientation is not None:
        o = np.asarray(orientation, dtype=np.float32).reshape(-1)
        if o.size >= 3:
            orient = o[:3].astype(np.float32)

    parts: list[np.ndarray] = []
    for field in fields:
        if field == "angular_velocity":
            parts.append(ang)
        elif field == "linear_acceleration":
            parts.append(lin)
        elif field == "orientation":
            parts.append(orient)
    if not parts:
        return np.zeros(3, dtype=np.float32)
    return np.concatenate(parts).astype(np.float32)


def pack_contact(fields: list[str], *, contact_count: int) -> np.ndarray:
    val = min(1.0, max(0.0, float(contact_count)))
    n = max(1, len(fields) or 1)
    return np.full(n, val, dtype=np.float32)


def pack_odom(
    fields: list[str],
    *,
    linear_velocity_x: float = 0.0,
    linear_velocity_y: float = 0.0,
    angular_velocity_z: float = 0.0,
) -> np.ndarray:
    scalars: dict[str, float] = {
        "linear_velocity_x": linear_velocity_x,
        "linear_velocity_y": linear_velocity_y,
        "angular_velocity_z": angular_velocity_z,
    }
    parts: list[np.ndarray] = []
    for field in fields:
        v = float(scalars.get(field, 0.0))
        parts.append(np.array([v], dtype=np.float32))
    if not parts:
        return np.zeros(1, dtype=np.float32)
    return np.concatenate(parts).astype(np.float32)


def pack_sensor_from_spec(kind: str, fields: list[str], raw: dict[str, Any]) -> np.ndarray:
    k = (kind or "").lower()
    if k == "imu":
        return pack_imu(
            fields,
            angular_velocity=raw.get("angular_velocity", np.zeros(3)),
            linear_acceleration=raw.get("linear_acceleration", np.zeros(3)),
            orientation=raw.get("orientation"),
        )
    if k == "contact":
        return pack_contact(fields, contact_count=int(raw.get("contact_count", 0)))
    if k == "odom":
        return pack_odom(
            fields,
            linear_velocity_x=float(raw.get("linear_velocity_x", 0.0)),
            linear_velocity_y=float(raw.get("linear_velocity_y", 0.0)),
            angular_velocity_z=float(raw.get("angular_velocity_z", 0.0)),
        )
    return np.zeros(sensor_term_dim(k, fields), dtype=np.float32)
