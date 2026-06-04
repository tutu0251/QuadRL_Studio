"""Compute grounded spawn height for geo exports (feet on z=0)."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _parse_vec3(text: str | None, default: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[float, float, float]:
    if not text:
        return default
    parts = text.split()
    if len(parts) < 3:
        return default
    return float(parts[0]), float(parts[1]), float(parts[2])


def _parse_rpy(text: str | None) -> tuple[float, float, float]:
    return _parse_vec3(text, (0.0, 0.0, 0.0))


def _rpy_to_quat(roll: float, pitch: float, yaw: float) -> tuple[float, float, float, float]:
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return x, y, z, w


def _quat_mul(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _quat_rotate(q: tuple[float, float, float, float], v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z, w = q
    vx, vy, vz = v
    ix = w * vx + y * vz - z * vy
    iy = w * vy + z * vx - x * vz
    iz = w * vz + x * vy - y * vx
    iw = -x * vx - y * vy - z * vz
    return (
        ix * w + iw * -x + iy * -z - iz * -y,
        iy * w + iw * -y + iz * -x - ix * -z,
        iz * w + iw * -z + ix * -y - iy * -x,
    )


def _compose(
    parent_pos: tuple[float, float, float],
    parent_rot: tuple[float, float, float, float],
    child_pos: tuple[float, float, float],
    child_rot: tuple[float, float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
    rotated = _quat_rotate(parent_rot, child_pos)
    pos = (parent_pos[0] + rotated[0], parent_pos[1] + rotated[1], parent_pos[2] + rotated[2])
    rot = _quat_mul(parent_rot, child_rot)
    return pos, rot


def _collision_half_extents(geom: ET.Element | None) -> tuple[float, float, float]:
    if geom is None:
        return 0.0, 0.0, 0.0
    box = geom.find("box")
    if box is not None:
        size = _parse_vec3(box.get("size"), (0.0, 0.0, 0.0))
        return size[0] / 2, size[1] / 2, size[2] / 2
    cyl = geom.find("cylinder")
    if cyl is not None:
        r = float(cyl.get("radius", "0"))
        h = float(cyl.get("length", "0")) / 2
        return r, h, r
    sph = geom.find("sphere")
    if sph is not None:
        r = float(sph.get("radius", "0"))
        return r, r, r
    return 0.05, 0.05, 0.05


def _min_z_for_collision(
    pos: tuple[float, float, float],
    rot: tuple[float, float, float, float],
    hx: float,
    hy: float,
    hz: float,
) -> float:
    min_z = math.inf
    for sx in (-hx, hx):
        for sy in (-hy, hy):
            for sz in (-hz, hz):
                corner = _quat_rotate(rot, (sx, sy, sz))
                min_z = min(min_z, pos[2] + corner[2])
    return min_z


def compute_min_collision_z(urdf_path: Path, joint_positions: dict[str, float] | None = None) -> float:
    """Lowest world Z of URDF collision geometry at the given joint positions."""
    root = ET.parse(urdf_path).getroot()
    joints = root.findall("joint")
    links = {link.get("name"): link for link in root.findall("link") if link.get("name")}

    children = {j.find("child").get("link") for j in joints if j.find("child") is not None}
    root_names = [name for name in links if name not in children]
    if not root_names:
        root_names = [next(iter(links))] if links else []

    joint_by_child: dict[str, ET.Element] = {}
    for joint in joints:
        child = joint.find("child")
        if child is not None and child.get("link"):
            joint_by_child[child.get("link")] = joint

    positions = joint_positions or {}

    def joint_angle(joint: ET.Element) -> float:
        name = joint.get("name") or ""
        if name in positions:
            return float(positions[name])
        return 0.0

    def joint_motion(joint: ET.Element) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
        jtype = (joint.get("type") or "fixed").lower()
        angle = joint_angle(joint)
        if jtype == "prismatic":
            axis = _parse_vec3((joint.find("axis") or ET.Element("axis")).get("xyz"), (0.0, 0.0, 1.0))
            n = math.sqrt(axis[0] ** 2 + axis[1] ** 2 + axis[2] ** 2) or 1.0
            offset = (axis[0] / n * angle, axis[1] / n * angle, axis[2] / n * angle)
            return offset, (0.0, 0.0, 0.0, 1.0)
        if jtype in ("revolute", "continuous"):
            axis = _parse_vec3((joint.find("axis") or ET.Element("axis")).get("xyz"), (0.0, 0.0, 1.0))
            n = math.sqrt(axis[0] ** 2 + axis[1] ** 2 + axis[2] ** 2) or 1.0
            ax, ay, az = axis[0] / n, axis[1] / n, axis[2] / n
            half = angle / 2
            s = math.sin(half)
            return (0.0, 0.0, 0.0), (ax * s, ay * s, az * s, math.cos(half))
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)

    transforms: dict[str, tuple[tuple[float, float, float], tuple[float, float, float, float]]] = {}

    def visit(link_name: str, parent_tf: tuple[tuple[float, float, float], tuple[float, float, float, float]]) -> None:
        link = links.get(link_name)
        if link is None:
            return
        transforms[link_name] = parent_tf
        for joint in joints:
            child = joint.find("child")
            if child is None or child.get("link") is None:
                continue
            if joint.find("parent") is None or joint.find("parent").get("link") != link_name:
                continue
            origin = joint.find("origin")
            oxyz = _parse_vec3(origin.get("xyz") if origin is not None else None)
            orpy = _parse_rpy(origin.get("rpy") if origin is not None else None)
            j_pos_rot = _rpy_to_quat(*orpy)
            motion_offset, motion_rot = joint_motion(joint)
            j_offset = (oxyz[0] + motion_offset[0], oxyz[1] + motion_offset[1], oxyz[2] + motion_offset[2])
            j_rot = _quat_mul(j_pos_rot, motion_rot)
            child_tf = _compose(parent_tf[0], parent_tf[1], j_offset, j_rot)
            visit(child.get("link"), child_tf)

    for root_name in root_names:
        visit(root_name, ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

    min_z = math.inf
    for link_name, (pos, rot) in transforms.items():
        link = links[link_name]
        for collision in link.findall("collision"):
            origin = collision.find("origin")
            oxyz = _parse_vec3(origin.get("xyz") if origin is not None else None)
            orpy = _parse_rpy(origin.get("rpy") if origin is not None else None)
            c_pos_rot = _rpy_to_quat(*orpy)
            col_pos, col_rot = _compose(pos, rot, oxyz, c_pos_rot)
            hx, hy, hz = _collision_half_extents(collision.find("geometry"))
            min_z = min(min_z, _min_z_for_collision(col_pos, col_rot, hx, hy, hz))

    return 0.0 if not math.isfinite(min_z) else min_z


def compute_grounded_spawn_z(urdf_path: Path, joint_positions: dict[str, float] | None = None) -> float:
    """Model-root Z so collision geometry rests on the ground plane (z=0)."""
    return -compute_min_collision_z(urdf_path, joint_positions)


def resolve_test_spawn_create_pose(project: str, cfg: Any) -> dict[str, float]:
    """
    Pose for ros_gz_sim create.

    Geo exports are authored feet-down in model space. default_pose spawn.z is the
    training reset height (with stand joints applied later), not the create offset.
    """
    from storage import project_storage

    exports = project_storage.exports_dir(project)
    urdf = exports / f"geo_{project}.urdf"

    grounded_z = 0.0
    if urdf.is_file():
        try:
            # Test spawn does not apply stand joint angles; Gazebo starts joints at 0.
            grounded_z = compute_grounded_spawn_z(urdf, None)
        except (ET.ParseError, OSError, ValueError):
            grounded_z = 0.0

    offset = cfg.spawn_offset
    return {
        "x": float(cfg.effective_spawn.get("x", 0.0)),
        "y": float(cfg.effective_spawn.get("y", 0.0)),
        "z": grounded_z + float(getattr(offset, "dz", 0.0)),
        "roll": float(cfg.effective_spawn.get("roll", 0.0)),
        "pitch": float(cfg.effective_spawn.get("pitch", 0.0)),
        "yaw": float(cfg.effective_spawn.get("yaw", 0.0)),
    }
