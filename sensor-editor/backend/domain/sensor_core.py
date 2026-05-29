"""Sensor editor business logic."""
from __future__ import annotations

import re

from domain.models import (
    ContactConfig,
    ImuConfig,
    LidarConfig,
    SensorCreate,
    SensorInstance,
    SensorKind,
    SensorModel,
    SensorPose,
    SensorUpdate,
    new_id,
    utc_now_iso,
)
from importer.ctrl_urdf_importer import parse_ctrl_urdf
from storage import project_storage


def _slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower()


def default_ros_topic(prefix: str, sensor_name: str) -> str:
    p = prefix.rstrip("/")
    return f"{p}/{_slug(sensor_name)}"


def _default_sensor_name(kind: SensorKind, parent_link: str) -> str:
    link = _slug(parent_link)
    if kind == SensorKind.IMU:
        return f"{link}_imu" if link else "imu"
    if kind == SensorKind.CONTACT:
        return f"{link}_contact" if link else "contact"
    return f"{link}_lidar" if link else "lidar"


class SensorCore:
    def __init__(self, model: SensorModel | None = None):
        self._model = model or SensorModel()

    def get_model(self) -> SensorModel:
        return self._model

    def set_model(self, model: SensorModel) -> None:
        self._model = model

    def import_ctrl_urdf(self, project_name: str) -> SensorModel:
        path = project_storage.ctrl_urdf_path(project_name)
        if not path.is_file():
            raise FileNotFoundError(
                f"Control URDF not found: {path}. Export from Control Editor first."
            )

        robot_name, links = parse_ctrl_urdf(path)
        ctrl_robot = project_storage.load_control_robot_name(project_name)
        if ctrl_robot:
            robot_name = ctrl_robot

        prefix = f"/{_slug(robot_name)}" if robot_name else "/quadruped"
        gz_name = robot_name or project_name

        if self._model.projectName == project_name and self._model.sensors:
            self._model.linkNames = links
            self._model.sourceCtrlUrdf = str(path)
            self._model.robotName = robot_name
            if not self._model.gzModelName:
                self._model.gzModelName = gz_name
            return self._model

        self._model = SensorModel(
            id=new_id(),
            projectName=project_name,
            robotName=robot_name,
            sourceCtrlUrdf=str(path),
            topicPrefix=prefix,
            gzModelName=gz_name,
            linkNames=links,
            metadata={
                "importedFrom": str(path),
                "importedAt": utc_now_iso(),
                "hasControllers": project_storage.ctrl_controllers_yaml_path(project_name).exists(),
            },
        )
        return self._model

    def bootstrap_quadruped(self) -> SensorModel:
        """Add base IMU + foot contacts from control_model child links."""
        if not self._model.linkNames:
            raise ValueError("Import ctrl URDF first")

        base_link = self._model.linkNames[0]
        for ln in self._model.linkNames:
            if ln in ("base", "base_link", "trunk", "body"):
                base_link = ln
                break

        existing = {s.parentLink for s in self._model.sensors if s.kind == SensorKind.CONTACT}
        foot_links = project_storage.load_control_child_links(self._model.projectName)
        if not foot_links:
            foot_links = [ln for ln in self._model.linkNames if "foot" in ln.lower() or ln.endswith("_foot")]

        if not any(s.kind == SensorKind.IMU for s in self._model.sensors):
            self.add_sensor(
                SensorCreate(
                    kind=SensorKind.IMU,
                    name="base_imu",
                    parentLink=base_link,
                )
            )

        for link in foot_links:
            if link in existing:
                continue
            if link not in self._model.linkNames:
                continue
            self.add_sensor(
                SensorCreate(
                    kind=SensorKind.CONTACT,
                    name=f"{_slug(link)}_contact",
                    parentLink=link,
                )
            )

        return self._model

    def update_topic_config(
        self,
        topic_prefix: str | None = None,
        gz_model_name: str | None = None,
        update_rate_default: float | None = None,
    ) -> SensorModel:
        if topic_prefix is not None:
            self._model.topicPrefix = topic_prefix
        if gz_model_name is not None:
            self._model.gzModelName = gz_model_name
        if update_rate_default is not None:
            self._model.updateRateDefault = update_rate_default
        return self._model

    def add_sensor(self, body: SensorCreate) -> SensorInstance:
        if body.parentLink not in self._model.linkNames:
            raise ValueError(f"Unknown link: {body.parentLink}")

        name = body.name or _default_sensor_name(body.kind, body.parentLink)
        rate = body.updateRate if body.updateRate is not None else self._model.updateRateDefault
        ros_topic = body.rosTopic or default_ros_topic(self._model.topicPrefix, name)

        inst = SensorInstance(
            id=new_id(),
            kind=body.kind,
            name=name,
            parentLink=body.parentLink,
            enabled=body.enabled,
            pose=body.pose or SensorPose(),
            rosTopic=ros_topic,
            updateRate=rate,
        )
        if body.kind == SensorKind.IMU:
            inst.imu = body.imu or ImuConfig()
        elif body.kind == SensorKind.CONTACT:
            inst.contact = body.contact or ContactConfig()
        else:
            inst.lidar = body.lidar or LidarConfig()

        self._model.sensors.append(inst)
        return inst

    def update_sensor(self, sensor_id: str, body: SensorUpdate) -> SensorInstance:
        inst = self._get_sensor(sensor_id)
        old_link = inst.parentLink
        if body.parentLink is not None and body.parentLink not in self._model.linkNames:
            raise ValueError(f"Unknown link: {body.parentLink}")

        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(inst, k, v)

        if body.parentLink is not None and body.parentLink != old_link:
            inst.name = _default_sensor_name(inst.kind, inst.parentLink)
            inst.rosTopic = default_ros_topic(self._model.topicPrefix, inst.name)
        elif body.name is not None and body.rosTopic is None:
            inst.rosTopic = default_ros_topic(self._model.topicPrefix, inst.name)

        return inst

    def remove_sensor(self, sensor_id: str) -> None:
        self._model.sensors = [s for s in self._model.sensors if s.id != sensor_id]

    def _get_sensor(self, sensor_id: str) -> SensorInstance:
        for s in self._model.sensors:
            if s.id == sensor_id:
                return s
        raise KeyError(f"Sensor not found: {sensor_id}")
