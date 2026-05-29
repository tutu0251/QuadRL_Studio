"""Kinematic and geometry validation."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Optional

from domain.math_utils import vec3_norm
from domain.models import (
    JointType,
    NamingConvention,
    PrimitiveType,
    RobotModel,
    ValidationIssue,
    ValidationResult,
    Vec3,
)


class GeometryValidator:
    def __init__(self, model: RobotModel):
        self.model = model
        self.issues: list[ValidationIssue] = []

    def _err(self, code: str, message: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None):
        self.issues.append(
            ValidationIssue(severity="error", code=code, message=message, entityType=entity_type, entityId=entity_id)
        )

    def _warn(self, code: str, message: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None):
        self.issues.append(
            ValidationIssue(severity="warning", code=code, message=message, entityType=entity_type, entityId=entity_id)
        )

    def validate(self) -> ValidationResult:
        self.issues = []
        self._check_duplicate_names()
        self._check_joint_links()
        self._check_same_link_joint()
        self._check_duplicate_parent_child()
        self._check_tree()
        self._check_zero_size_shapes()
        self._check_joint_axes()
        self._check_joint_limits()
        self._check_orphan_links()
        self._check_naming_convention()
        self._check_mirror_asymmetry()
        self._check_foot_height()
        self._check_self_overlap()
        self._check_placeholder_inertial()
        self._check_capsule_sdf_fallback()
        errors = [i for i in self.issues if i.severity == "error"]
        return ValidationResult(valid=len(errors) == 0, issues=self.issues)

    def validate_urdf_xml(self, urdf_text: str) -> None:
        try:
            root = ET.fromstring(urdf_text)
        except ET.ParseError as e:
            self._err("urdf_parse", f"URDF parse error: {e}", "robot")
            return
        if root.tag != "robot":
            self._err("urdf_root", "URDF root must be <robot>", "robot")
        link_names = {el.get("name") for el in root.findall("link")}
        for joint in root.findall("joint"):
            parent = joint.find("parent")
            child = joint.find("child")
            if parent is None or child is None:
                self._err("urdf_joint_missing", f"Joint '{joint.get('name')}' missing parent/child", "joint")
                continue
            pn, cn = parent.get("link"), child.get("link")
            if pn not in link_names:
                self._err("urdf_floating", f"Joint '{joint.get('name')}' parent '{pn}' not a link", "joint")
            if cn not in link_names:
                self._err("urdf_floating", f"Joint '{joint.get('name')}' child '{cn}' not a link", "joint")

    def _check_duplicate_names(self):
        link_names = [l.name for l in self.model.links]
        joint_names = [j.name for j in self.model.joints]
        for name in set(link_names):
            if link_names.count(name) > 1:
                self._err("duplicate_link_name", f"Duplicate link name: {name}", "link")
        for name in set(joint_names):
            if joint_names.count(name) > 1:
                self._err("duplicate_joint_name", f"Duplicate joint name: {name}", "joint")

    def _check_joint_links(self):
        link_ids = {l.id for l in self.model.links}
        for j in self.model.joints:
            if j.parentLinkId not in link_ids:
                self._err("missing_parent_link", f"Joint '{j.name}' missing parent link", "joint", j.id)
            if j.childLinkId not in link_ids:
                self._err("missing_child_link", f"Joint '{j.name}' missing child link", "joint", j.id)

    def _check_same_link_joint(self):
        for j in self.model.joints:
            if j.parentLinkId == j.childLinkId:
                self._err("self_joint", f"Joint '{j.name}' connects link to itself", "joint", j.id)

    def _check_duplicate_parent_child(self):
        pairs: dict[tuple[str, str], list[str]] = defaultdict(list)
        for j in self.model.joints:
            pairs[(j.parentLinkId, j.childLinkId)].append(j.name)
        for (parent_id, child_id), names in pairs.items():
            if len(names) < 2:
                continue
            parent = next((l.name for l in self.model.links if l.id == parent_id), parent_id)
            child = next((l.name for l in self.model.links if l.id == child_id), child_id)
            self._err(
                "duplicate_parent_child",
                f"Multiple joints connect '{parent}' → '{child}': {names}",
                "joint",
            )

    def _check_tree(self):
        if not self.model.links:
            return
        children = {j.childLinkId for j in self.model.joints}
        roots = [l for l in self.model.links if l.id not in children]
        if len(roots) == 0:
            self._err("cyclic_tree", "No root link found (possible cycle)", "robot")
        if len(roots) > 1:
            self._warn("multiple_roots", f"Multiple root links: {[r.name for r in roots]}", "robot")

        adj: dict[str, list[str]] = defaultdict(list)
        for j in self.model.joints:
            adj[j.parentLinkId].append(j.childLinkId)

        visited: set[str] = set()
        stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            stack.add(node)
            for child in adj.get(node, []):
                if child not in visited:
                    if dfs(child):
                        return True
                elif child in stack:
                    self._err("cyclic_tree", "Cycle detected in kinematic tree", "robot")
                    return True
            stack.remove(node)
            return False

        for root in roots:
            dfs(root.id)

        for l in self.model.links:
            if l.id not in visited and len(self.model.joints) > 0:
                self._warn("disconnected_link", f"Link '{l.name}' is disconnected from tree", "link", l.id)

    def _check_zero_size_shapes(self):
        for link in self.model.links:
            for shape in link.shapes:
                if not shape.dimensions or any(d <= 0 for d in shape.dimensions):
                    self._err("zero_size_shape", f"Zero-size shape on link '{link.name}'", "shape", shape.id)

    def _check_joint_axes(self):
        for j in self.model.joints:
            if j.type in (JointType.REVOLUTE, JointType.CONTINUOUS, JointType.PRISMATIC):
                if vec3_norm(j.axis) < 1e-6:
                    self._err("invalid_joint_axis", f"Joint '{j.name}' has zero axis", "joint", j.id)

    def _check_joint_limits(self):
        for j in self.model.joints:
            if j.type == JointType.REVOLUTE and j.lowerLimit >= j.upperLimit:
                self._err("invalid_joint_limits", f"Joint '{j.name}' has invalid limits", "joint", j.id)

    def _check_orphan_links(self):
        child_links = {j.childLinkId for j in self.model.joints}
        roots = {l.id for l in self.model.links if l.id not in child_links}
        for l in self.model.links:
            if l.id not in roots and not l.parentJointId:
                self._warn("child_without_joint", f"Child link '{l.name}' has no parent joint recorded", "link", l.id)

    def _check_naming_convention(self):
        conv = self.model.namingConvention
        for j in self.model.joints:
            if j.type == JointType.FIXED:
                continue
            if not j.name.endswith("_joint"):
                self._warn("naming_joint_suffix", f"Joint '{j.name}' should end with '_joint'", "joint", j.id)
            if conv == NamingConvention.ROS2_UPPER:
                parts = j.name.split("_")
                if parts and len(parts[0]) == 2 and parts[0].islower():
                    self._warn(
                        "naming_ros2_prefix",
                        f"Joint '{j.name}' expected ROS2 prefix like FL_ not {parts[0]}",
                        "joint",
                        j.id,
                    )

    def _check_mirror_asymmetry(self):
        pairs = [("fl", "fr"), ("rl", "rr"), ("FL", "FR"), ("RL", "RR")]
        for left, right in pairs:
            ll = [l for l in self.model.links if l.name.startswith(left)]
            rl = [l for l in self.model.links if l.name.startswith(right)]
            if ll and not rl:
                self._warn("mirror_asymmetry", f"Leg '{left}' exists without mirrored '{right}'", "robot")
            if len(ll) != len(rl) and ll and rl:
                self._warn("mirror_asymmetry", f"Leg pair {left}/{right} link count mismatch", "robot")

    def _check_foot_height(self):
        from domain.measure import compute_world_transforms
        tf = compute_world_transforms(self.model)
        tolerance = 0.05
        feet = [l for l in self.model.links if "foot" in l.name.lower()]
        for foot in feet:
            if foot.id not in tf:
                continue
            z = tf[foot.id].position.z
            for s in foot.shapes:
                if s.type == PrimitiveType.SPHERE and s.dimensions:
                    z -= s.dimensions[0]
            if abs(z) > tolerance:
                self._warn("foot_height", f"Foot '{foot.name}' may not be near ground (z≈{z:.3f})", "link", foot.id)

    def _check_self_overlap(self):
        boxes: list[tuple[str, tuple]] = []
        for link in self.model.links:
            for s in link.shapes:
                if s.type == PrimitiveType.BOX and len(s.dimensions) >= 3:
                    hx, hy, hz = [d / 2 for d in s.dimensions[:3]]
                    px, py, pz = s.localPosition.x, s.localPosition.y, s.localPosition.z
                    boxes.append((link.name, (px - hx, py - hy, pz - hz, px + hx, py + hy, pz + hz)))
        for i, (na, a) in enumerate(boxes):
            for nb, b in boxes[i + 1:]:
                if self._aabb_overlap(a, b):
                    self._warn("self_overlap", f"Possible overlap between '{na}' and '{nb}'", "robot")

    def _check_placeholder_inertial(self):
        for link in self.model.links:
            if link.inertial.mass == 1.0:
                self._warn("placeholder_mass", f"Link '{link.name}' uses placeholder mass=1.0", "link", link.id)

    def _check_capsule_sdf_fallback(self):
        for link in self.model.links:
            for s in link.shapes:
                if s.type == PrimitiveType.CAPSULE:
                    self._warn(
                        "capsule_sdf_fallback",
                        f"Capsule on '{link.name}' exports as cylinder in SDF",
                        "shape",
                        s.id,
                    )

    @staticmethod
    def _aabb_overlap(a, b) -> bool:
        return all(a[i] <= b[i + 3] and b[i] <= a[i + 3] for i in range(3))
