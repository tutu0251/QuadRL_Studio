"""Gazebo Fortress topic templates for ros_gz_bridge."""
from __future__ import annotations

from domain.models import SensorInstance, SensorKind


def gz_imu_topic(gz_model: str, link: str, sensor_name: str) -> str:
    return f"/world/default/model/{gz_model}/link/{link}/sensor/{sensor_name}/imu"


def gz_contact_topic(gz_model: str, link: str, sensor_name: str) -> str:
    return f"/world/default/model/{gz_model}/link/{link}/sensor/{sensor_name}/contacts"


def gz_lidar_topic(gz_model: str, link: str, sensor_name: str) -> str:
    return f"/world/default/model/{gz_model}/link/{link}/sensor/{sensor_name}/scan"


def gz_topic_for_sensor(gz_model: str, sensor: SensorInstance) -> str:
    if sensor.kind == SensorKind.IMU:
        return gz_imu_topic(gz_model, sensor.parentLink, sensor.name)
    if sensor.kind == SensorKind.CONTACT:
        return gz_contact_topic(gz_model, sensor.parentLink, sensor.name)
    return gz_lidar_topic(gz_model, sensor.parentLink, sensor.name)


ROS_MSG_TYPES = {
    SensorKind.IMU: ("sensor_msgs/msg/Imu", "gz.msgs.IMU"),
    SensorKind.CONTACT: ("ros_gz_interfaces/msg/Contacts", "gz.msgs.Contacts"),
    SensorKind.LIDAR: ("sensor_msgs/msg/LaserScan", "gz.msgs.LaserScan"),
}
