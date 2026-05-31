"""Append Gazebo sensor blocks to ctrl URDF → sens_*_rl.urdf."""
from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path

from domain.link_preservation import assert_link_topology_unchanged
from domain.models import LidarConfig, OdomConfig, SensorInstance, SensorKind, SensorModel

QRL_ATTR = "qrl_sensor_id"


def _indent(elem: ET.Element, level: int = 0) -> None:
    pad = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + "  "
        for child in elem:
            _indent(child, level + 1)
        child.tail = pad
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad


def _pose_text(pose) -> str:
    x, y, z = pose.xyz
    r, p, yaw = pose.rpy
    return f"{x} {y} {z} {r} {p} {yaw}"


def _has_nonzero_pose(pose) -> bool:
    return any(abs(v) > 1e-9 for v in (*pose.xyz, *pose.rpy))


def _build_imu_children(sensor: SensorInstance) -> list[ET.Element]:
    imu_cfg = sensor.imu
    enable_ori = imu_cfg.enableOrientation if imu_cfg else True
    imu_el = ET.Element("imu")
    for tag in ("angular_velocity", "linear_acceleration"):
        parent = ET.SubElement(imu_el, tag)
        for axis in ("x", "y", "z"):
            ET.SubElement(parent, axis)
    if enable_ori:
        orient = ET.SubElement(imu_el, "orientation")
        for axis in ("x", "y", "z", "w"):
            ET.SubElement(orient, axis)
    return [imu_el]


def _build_contact_children(sensor: SensorInstance) -> list[ET.Element]:
    collision = "collision"
    if sensor.contact and sensor.contact.collisionName:
        collision = sensor.contact.collisionName
    contact = ET.Element("contact")
    col = ET.SubElement(contact, "collision")
    col.text = collision
    return [contact]


def _build_lidar_children(sensor: SensorInstance) -> list[ET.Element]:
    cfg: LidarConfig = sensor.lidar or LidarConfig()
    lidar = ET.Element("lidar")
    scan = ET.SubElement(lidar, "scan")
    horiz = ET.SubElement(scan, "horizontal")
    ET.SubElement(horiz, "samples").text = str(cfg.samples)
    res = 2.0 * cfg.horizontalFov / max(cfg.samples, 1)
    ET.SubElement(horiz, "resolution").text = str(res)
    ET.SubElement(horiz, "min_angle").text = str(-cfg.horizontalFov / 2)
    ET.SubElement(horiz, "max_angle").text = str(cfg.horizontalFov / 2)
    if cfg.verticalSamples > 1:
        vert = ET.SubElement(scan, "vertical")
        ET.SubElement(vert, "samples").text = str(cfg.verticalSamples)
        ET.SubElement(vert, "resolution").text = "0.1"
        ET.SubElement(vert, "min_angle").text = "-0.2"
        ET.SubElement(vert, "max_angle").text = "0.2"
    range_el = ET.SubElement(lidar, "range")
    ET.SubElement(range_el, "min").text = str(cfg.minRange)
    ET.SubElement(range_el, "max").text = str(cfg.maxRange)
    ET.SubElement(range_el, "resolution").text = "0.01"
    return [lidar]


def _build_odom_plugin(sensor: SensorInstance, model: SensorModel) -> ET.Element:
    cfg: OdomConfig = sensor.odom or OdomConfig()
    plugin = ET.Element(
        "plugin",
        filename="ignition-gazebo-odometry-publisher-system",
        name="ignition::gazebo::systems::OdometryPublisher",
    )
    plugin.set(QRL_ATTR, sensor.id)
    odom_frame = cfg.odomFrame or f"{model.gzModelName}/odom"
    base_frame = cfg.robotBaseFrame or sensor.parentLink
    ET.SubElement(plugin, "odom_frame").text = odom_frame
    ET.SubElement(plugin, "robot_base_frame").text = base_frame
    ET.SubElement(plugin, "odom_publish_frequency").text = str(int(sensor.updateRate))
    ET.SubElement(plugin, "dimensions").text = str(cfg.dimensions)
    if cfg.noiseStddev > 0:
        ET.SubElement(plugin, "noise_stddev").text = str(cfg.noiseStddev)
    return plugin


def _gazebo_sensor_type(kind: SensorKind) -> str:
    if kind == SensorKind.LIDAR:
        return "gpu_lidar"
    return kind.value


def _build_sensor_element(sensor: SensorInstance) -> ET.Element:
    gz_type = _gazebo_sensor_type(sensor.kind)
    sel = ET.Element("sensor", name=sensor.name, type=gz_type)
    sel.set(QRL_ATTR, sensor.id)
    ET.SubElement(sel, "always_on").text = "1"
    ET.SubElement(sel, "update_rate").text = str(int(sensor.updateRate))
    if _has_nonzero_pose(sensor.pose):
        pose_el = ET.SubElement(sel, "pose")
        pose_el.text = _pose_text(sensor.pose)
    if sensor.kind == SensorKind.IMU:
        children = _build_imu_children(sensor)
    elif sensor.kind == SensorKind.CONTACT:
        children = _build_contact_children(sensor)
    else:
        children = _build_lidar_children(sensor)
    for ch in children:
        sel.append(ch)
    return sel


def _strip_qrl_managed(root: ET.Element) -> None:
    for gz in list(root.findall("gazebo")):
        for sensor in list(gz.findall("sensor")):
            if sensor.get(QRL_ATTR):
                gz.remove(sensor)
        for plugin in list(gz.findall("plugin")):
            if plugin.get(QRL_ATTR):
                gz.remove(plugin)
        if len(gz) == 0 and gz.get("reference"):
            root.remove(gz)


def _find_or_create_gazebo(root: ET.Element, link: str) -> ET.Element:
    for gz in root.findall("gazebo"):
        if gz.get("reference") == link:
            return gz
    gz = ET.SubElement(root, "gazebo", reference=link)
    return gz


def _find_or_create_model_gazebo(root: ET.Element) -> ET.Element:
    for gz in root.findall("gazebo"):
        if gz.get("reference") is None:
            return gz
    return ET.SubElement(root, "gazebo")


def merge_sensors_into_urdf(
    model: SensorModel,
    ctrl_urdf_path: Path,
    output_path: Path,
) -> Path:
    tree = ET.parse(ctrl_urdf_path)
    root = tree.getroot()
    before_root = copy.deepcopy(root)
    _strip_qrl_managed(root)

    by_link: dict[str, list[SensorInstance]] = {}
    odom_sensors: list[SensorInstance] = []
    for s in model.sensors:
        if not s.enabled:
            continue
        if s.kind == SensorKind.ODOM:
            odom_sensors.append(s)
            continue
        by_link.setdefault(s.parentLink, []).append(s)

    for link, sensors in by_link.items():
        gz = _find_or_create_gazebo(root, link)
        for sensor in sensors:
            gz.append(_build_sensor_element(sensor))

    if odom_sensors:
        gz_model = _find_or_create_model_gazebo(root)
        for sensor in odom_sensors:
            gz_model.append(_build_odom_plugin(sensor, model))

    assert_link_topology_unchanged(before_root, root, step="sensor URDF merge")

    _indent(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="unicode", xml_declaration=True)
    return output_path
