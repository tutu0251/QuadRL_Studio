"""Auto-estimate link mass, COM, and inertia from primitive shapes (uniform density)."""
from __future__ import annotations

import math

from domain.models import Inertial, Link, PrimitiveShape, PrimitiveType, Vec3
from domain.math_utils import quat_rotate_vec


def _box_props(dims: list[float], density: float) -> tuple[float, Vec3, tuple[float, float, float, float, float, float]]:
    sx, sy, sz = dims[0], dims[1], dims[2]
    mass = density * sx * sy * sz
    ixx = mass * (sy**2 + sz**2) / 12.0
    iyy = mass * (sx**2 + sz**2) / 12.0
    izz = mass * (sx**2 + sy**2) / 12.0
    return mass, Vec3(), (ixx, 0.0, 0.0, iyy, 0.0, izz)


def _cylinder_props(r: float, length: float, density: float) -> tuple[float, Vec3, tuple[float, float, float, float, float, float]]:
    mass = density * math.pi * r**2 * length
    i_perp = mass * (3 * r**2 + length**2) / 12.0
    i_ax = 0.5 * mass * r**2
    return mass, Vec3(), (i_perp, 0.0, 0.0, i_perp, 0.0, i_ax)


def _sphere_props(r: float, density: float) -> tuple[float, Vec3, tuple[float, float, float, float, float, float]]:
    mass = density * (4.0 / 3.0) * math.pi * r**3
    i = 0.4 * mass * r**2
    return mass, Vec3(), (i, 0.0, 0.0, i, 0.0, i)


def _shape_props(shape: PrimitiveShape, density: float):
    d = shape.dimensions
    t = shape.type
    if t == PrimitiveType.BOX:
        return _box_props(d, density)
    if t == PrimitiveType.CYLINDER:
        length = d[1] if len(d) > 1 else d[0]
        return _cylinder_props(d[0], length, density)
    if t == PrimitiveType.SPHERE:
        return _sphere_props(d[0], density)
    if t == PrimitiveType.CAPSULE:
        r = d[0]
        length = d[1] if len(d) > 1 else 0.1
        return _cylinder_props(r, max(length, 2 * r), density)
    return _box_props([0.1, 0.1, 0.1], density)


def estimate_link_inertial(link: Link, density: float = 1000.0) -> Inertial:
    """Combine shape inertias about link origin using parallel axis theorem."""
    if not link.shapes:
        return link.inertial

    total_mass = 0.0
    com = Vec3()
    ixx = iyy = izz = ixy = ixz = iyz = 0.0

    for shape in link.shapes:
        m, local_com, (s_ixx, s_ixy, s_ixz, s_iyy, s_iyz, s_izz) = _shape_props(shape, density)
        offset = shape.localPosition
        # rotate offset by shape orientation
        world_offset = quat_rotate_vec(shape.localRotation, offset)
        cx = world_offset.x + local_com.x
        cy = world_offset.y + local_com.y
        cz = world_offset.z + local_com.z

        total_mass += m
        com.x += m * cx
        com.y += m * cy
        com.z += m * cz

        # parallel axis to link origin
        d2 = cx**2 + cy**2 + cz**2
        pxx = m * (cy**2 + cz**2)
        pyy = m * (cx**2 + cz**2)
        pzz = m * (cx**2 + cy**2)

        ixx += s_ixx + pxx
        iyy += s_iyy + pyy
        izz += s_izz + pzz
        ixy += s_ixy + m * cx * cy
        ixz += s_ixz + m * cx * cz
        iyz += s_iyz + m * cy * cz

    if total_mass < 1e-9:
        return link.inertial

    com.x /= total_mass
    com.y /= total_mass
    com.z /= total_mass

    return Inertial(
        mass=total_mass,
        com=com,
        comRotation=link.inertial.comRotation,
        ixx=ixx,
        ixy=ixy,
        ixz=ixz,
        iyy=iyy,
        iyz=iyz,
        izz=izz,
    )
