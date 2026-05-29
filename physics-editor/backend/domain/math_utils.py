"""Quaternion and transform utilities."""
from __future__ import annotations

import math

from domain.models import Quat, Vec3


def quat_normalize(q: Quat) -> Quat:
    n = math.sqrt(q.x**2 + q.y**2 + q.z**2 + q.w**2) or 1.0
    return Quat(x=q.x / n, y=q.y / n, z=q.z / n, w=q.w / n)


def quat_to_rpy(q: Quat) -> tuple[float, float, float]:
    q = quat_normalize(q)
    x, y, z, w = q.x, q.y, q.z, q.w
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2, sinp) if abs(sinp) >= 1 else math.asin(sinp)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return roll, pitch, yaw


def rpy_to_quat(roll: float, pitch: float, yaw: float) -> Quat:
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return Quat(
        x=sr * cp * cy - cr * sp * sy,
        y=cr * sp * cy + sr * cp * sy,
        z=cr * cp * sy - sr * sp * cy,
        w=cr * cp * cy + sr * sp * sy,
    )


def quat_multiply(a: Quat, b: Quat) -> Quat:
    return Quat(
        x=a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
        y=a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
        z=a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
        w=a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
    )


def quat_rotate_vec(q: Quat, v: Vec3) -> Vec3:
    qn = quat_normalize(q)
    qv = Quat(x=v.x, y=v.y, z=v.z, w=0)
    qi = Quat(x=-qn.x, y=-qn.y, z=-qn.z, w=qn.w)
    r = quat_multiply(quat_multiply(qn, qv), qi)
    return Vec3(x=r.x, y=r.y, z=r.z)


def vec3_norm(v: Vec3) -> float:
    return math.sqrt(v.x**2 + v.y**2 + v.z**2)


def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(x=a.x + b.x, y=a.y + b.y, z=a.z + b.z)
