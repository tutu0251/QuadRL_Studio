"""GeometryCore: robot model operations."""
from __future__ import annotations

import copy
import math
from typing import Optional

from domain.models import (
    Frame,
    Joint,
    JointType,
    Link,
    NamingConvention,
    Pose,
    PrimitiveShape,
    PrimitiveType,
    Quat,
    RobotModel,
    Vec3,
    new_id,
)
from templates.registry import insert_template


class GeometryCore:
    def __init__(self, model: Optional[RobotModel] = None):
        self.model = model or RobotModel()

    def create_project(self, name: str) -> RobotModel:
        self.model = RobotModel(name=name)
        base = Link(
            name="base_link",
            shapes=[
                PrimitiveShape(type=PrimitiveType.BOX, dimensions=[0.3, 0.15, 0.06], color="#777777")
            ],
        )
        self.model.links.append(base)
        self.model.poses.append(Pose(name="standing", jointValues={}))
        return self.model

    def load(self, model: RobotModel) -> RobotModel:
        self.model = model
        return self.model

    def get_model(self) -> RobotModel:
        return self.model

    def set_naming_convention(self, convention: NamingConvention) -> None:
        self.model.namingConvention = convention

    def find_link(self, link_id: str) -> Optional[Link]:
        return next((l for l in self.model.links if l.id == link_id), None)

    def find_joint(self, joint_id: str) -> Optional[Joint]:
        return next((j for j in self.model.joints if j.id == joint_id), None)

    def add_child_link(self, parent_link_id: str, name: str, joint_name: str, joint_type: JointType = JointType.REVOLUTE) -> tuple[Link, Joint]:
        parent = self.find_link(parent_link_id)
        if not parent:
            raise ValueError("Parent link not found")
        child = Link(name=name)
        joint = Joint(
            name=joint_name,
            parentLinkId=parent_link_id,
            childLinkId=child.id,
            type=joint_type,
        )
        child.parentJointId = joint.id
        self.model.links.append(child)
        self.model.joints.append(joint)
        return child, joint

    def add_link(self, name: str, parent_joint_id: Optional[str] = None) -> Link:
        link = Link(name=name, parentJointId=parent_joint_id)
        self.model.links.append(link)
        return link

    def remove_link(self, link_id: str) -> bool:
        link = self.find_link(link_id)
        if not link:
            return False
        to_remove = {link_id}
        changed = True
        while changed:
            changed = False
            for j in self.model.joints:
                if j.parentLinkId in to_remove and j.childLinkId not in to_remove:
                    to_remove.add(j.childLinkId)
                    changed = True
        self.model.links = [l for l in self.model.links if l.id not in to_remove]
        self.model.joints = [
            j for j in self.model.joints
            if j.parentLinkId not in to_remove and j.childLinkId not in to_remove
        ]
        return True

    def rename_link(self, link_id: str, name: str) -> Optional[Link]:
        link = self.find_link(link_id)
        if link:
            link.name = name
        return link

    def add_joint(
        self,
        name: str,
        parent_link_id: str,
        child_link_id: str,
        joint_type: JointType = JointType.REVOLUTE,
    ) -> Joint:
        if parent_link_id == child_link_id:
            raise ValueError("Joint cannot connect link to itself")
        joint = Joint(
            name=name,
            parentLinkId=parent_link_id,
            childLinkId=child_link_id,
            type=joint_type,
        )
        self.model.joints.append(joint)
        child = self.find_link(child_link_id)
        if child:
            child.parentJointId = joint.id
        return joint

    def remove_joint(self, joint_id: str) -> bool:
        joint = self.find_joint(joint_id)
        if not joint:
            return False
        child = self.find_link(joint.childLinkId)
        if child:
            child.parentJointId = None
        self.model.joints = [j for j in self.model.joints if j.id != joint_id]
        return True

    def rename_joint(self, joint_id: str, name: str) -> Optional[Joint]:
        joint = self.find_joint(joint_id)
        if joint:
            joint.name = name
        return joint

    def add_shape(self, link_id: str, shape_type: PrimitiveType) -> Optional[PrimitiveShape]:
        link = self.find_link(link_id)
        if not link:
            return None
        defaults = {
            PrimitiveType.BOX: [0.1, 0.1, 0.1],
            PrimitiveType.CYLINDER: [0.05, 0.1],
            PrimitiveType.SPHERE: [0.05],
            PrimitiveType.CAPSULE: [0.03, 0.1],
        }
        shape = PrimitiveShape(type=shape_type, dimensions=defaults.get(shape_type, [0.1]))
        link.shapes.append(shape)
        return shape

    def remove_shape(self, link_id: str, shape_id: str) -> bool:
        link = self.find_link(link_id)
        if not link:
            return False
        before = len(link.shapes)
        link.shapes = [s for s in link.shapes if s.id != shape_id]
        return len(link.shapes) < before

    def update_shape_dimensions(self, link_id: str, shape_id: str, dimensions: list[float]) -> Optional[PrimitiveShape]:
        link = self.find_link(link_id)
        if not link:
            return None
        for s in link.shapes:
            if s.id == shape_id:
                s.dimensions = dimensions
                return s
        return None

    def update_shape_transform(
        self, link_id: str, shape_id: str, position: Vec3, rotation: Quat
    ) -> Optional[PrimitiveShape]:
        link = self.find_link(link_id)
        if not link:
            return None
        for s in link.shapes:
            if s.id == shape_id:
                s.localPosition = position
                s.localRotation = rotation
                return s
        return None

    def update_shape_color(self, link_id: str, shape_id: str, color: str) -> Optional[PrimitiveShape]:
        link = self.find_link(link_id)
        if not link:
            return None
        for s in link.shapes:
            if s.id == shape_id:
                s.color = color
                return s
        return None

    def update_joint(self, joint_id: str, **kwargs) -> Optional[Joint]:
        joint = self.find_joint(joint_id)
        if not joint:
            return None
        for k, v in kwargs.items():
            if hasattr(joint, k) and v is not None:
                setattr(joint, k, v)
        if "axis" in kwargs and kwargs["axis"] is not None:
            from domain.math_utils import vec3_normalize
            joint.axis = vec3_normalize(joint.axis)
        return joint

    def update_link_frame(self, link_id: str, frame: Frame) -> Optional[Link]:
        link = self.find_link(link_id)
        if link:
            link.frame = frame
        return link

    def add_pose(self, name: str) -> Pose:
        values = {j.id: j.defaultValue for j in self.model.joints if j.type != JointType.FIXED}
        pose = Pose(name=name, jointValues=values)
        self.model.poses.append(pose)
        return pose

    def save_pose(self, pose_id: str) -> Optional[Pose]:
        pose = next((p for p in self.model.poses if p.id == pose_id), None)
        if pose:
            pose.jointValues = {j.id: j.defaultValue for j in self.model.joints if j.type != JointType.FIXED}
        return pose

    def load_pose(self, pose_id: str) -> Optional[Pose]:
        pose = next((p for p in self.model.poses if p.id == pose_id), None)
        if not pose:
            return None
        for j in self.model.joints:
            if j.id in pose.jointValues:
                j.defaultValue = pose.jointValues[j.id]
        return pose

    def _duplicate_leg(self, source_prefix: str, target_prefix: str, mirror_y: bool) -> RobotModel:
        src_links = [l for l in self.model.links if l.name.startswith(source_prefix)]
        if not src_links:
            return self.model
        self.model.links = [l for l in self.model.links if not l.name.startswith(target_prefix)]
        self.model.joints = [j for j in self.model.joints if not j.name.startswith(target_prefix)]

        id_map: dict[str, str] = {}
        new_links: list[Link] = []
        for link in src_links:
            nl = copy.deepcopy(link)
            old_id = nl.id
            nl.id = new_id()
            id_map[old_id] = nl.id
            nl.name = link.name.replace(source_prefix, target_prefix, 1)
            for s in nl.shapes:
                s.id = new_id()
                if mirror_y:
                    s.localPosition.y *= -1
                    s.localRotation.y *= -1
            if mirror_y:
                nl.frame.position.y *= -1
            new_links.append(nl)

        new_joints: list[Joint] = []
        src_joints = [j for j in self.model.joints if j.name.startswith(source_prefix)]
        for joint in src_joints:
            nj = copy.deepcopy(joint)
            old_id = nj.id
            nj.id = new_id()
            id_map[old_id] = nj.id
            nj.name = joint.name.replace(source_prefix, target_prefix, 1)
            nj.parentLinkId = id_map.get(joint.parentLinkId, joint.parentLinkId)
            nj.childLinkId = id_map.get(joint.childLinkId, joint.childLinkId)
            if mirror_y:
                nj.originPosition.y *= -1
                nj.axis.y *= -1
            new_joints.append(nj)

        for nl in new_links:
            if nl.parentJointId and nl.parentJointId in id_map:
                nl.parentJointId = id_map[nl.parentJointId]
            self.model.links.append(nl)
        self.model.joints.extend(new_joints)
        return self.model

    def mirror_leg(self, source_prefix: str, target_prefix: str) -> RobotModel:
        return self._duplicate_leg(source_prefix, target_prefix, mirror_y=True)

    def copy_leg(self, source_prefix: str, target_prefix: str) -> RobotModel:
        return self._duplicate_leg(source_prefix, target_prefix, mirror_y=False)

    def apply_template(self, template_id: str) -> RobotModel:
        return insert_template(self.model, template_id)

    def measure_distance(self, link_a_id: str, link_b_id: str) -> Optional[float]:
        from domain.measure import measure_distance
        r = measure_distance(self.model, link_a_id, link_b_id)
        return r.value if r else None

    def check_naming_conventions(self) -> list[str]:
        issues = []
        conv = self.model.namingConvention
        for link in self.model.links:
            if not link.name.replace("_", "").replace("-", "").isalnum():
                issues.append(f"Link '{link.name}' should be alphanumeric with underscores")
        for joint in self.model.joints:
            if joint.type != JointType.FIXED and not joint.name.endswith("_joint"):
                issues.append(f"Joint '{joint.name}' should end with '_joint'")
            if conv == NamingConvention.ROS2_UPPER:
                parts = joint.name.split("_")
                if parts and parts[0].islower() and len(parts[0]) == 2:
                    issues.append(f"Joint '{joint.name}' should use ROS2 prefix like FL_ not {parts[0]}")
        return issues
