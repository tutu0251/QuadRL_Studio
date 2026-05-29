"""Inertia tensor utilities (principal axes, validation)."""
from __future__ import annotations

import numpy as np

from domain.models import Quat, Vec3
from domain.math_utils import quat_normalize, rpy_to_quat


def inertia_matrix(ixx: float, ixy: float, ixz: float, iyy: float, iyz: float, izz: float) -> np.ndarray:
    return np.array([[ixx, ixy, ixz], [ixy, iyy, iyz], [ixz, iyz, izz]], dtype=float)


def principal_axes(ixx: float, ixy: float, ixz: float, iyy: float, iyz: float, izz: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (eigenvalues ascending, 3x3 rotation columns = principal axis directions in link frame)."""
    m = inertia_matrix(ixx, ixy, ixz, iyy, iyz, izz)
    vals, vecs = np.linalg.eigh(m)
    return vals, vecs


def is_positive_definite(ixx: float, ixy: float, ixz: float, iyy: float, iyz: float, izz: float) -> bool:
    vals, _ = principal_axes(ixx, ixy, ixz, iyy, iyz, izz)
    return bool(np.all(vals > 1e-9))


def satisfies_triangle_inequalities(ixx: float, iyy: float, izz: float) -> bool:
    return ixx + iyy > izz and ixx + izz > iyy and iyy + izz > ixx


def rotation_matrix_to_quat(r: np.ndarray) -> Quat:
    """Convert 3x3 rotation matrix to quaternion."""
    m = r
    tr = float(m[0, 0] + m[1, 1] + m[2, 2])
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    return quat_normalize(Quat(x=float(x), y=float(y), z=float(z), w=float(w)))


def principal_axes_quat(ixx: float, ixy: float, ixz: float, iyy: float, iyz: float, izz: float) -> Quat:
    _, vecs = principal_axes(ixx, ixy, ixz, iyy, iyz, izz)
    return rotation_matrix_to_quat(vecs)


def axis_vec_from_column(vecs: np.ndarray, col: int) -> Vec3:
    v = vecs[:, col]
    n = float(np.linalg.norm(v)) or 1.0
    return Vec3(x=float(v[0] / n), y=float(v[1] / n), z=float(v[2] / n))


def parse_rpy_attr(rpy: str) -> Quat:
    parts = [float(x) for x in rpy.split()]
    if len(parts) != 3:
        return Quat(w=1.0)
    return rpy_to_quat(parts[0], parts[1], parts[2])
