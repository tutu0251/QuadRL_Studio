"""Physics model operations."""
from __future__ import annotations

from typing import Optional

from domain.estimate import estimate_link_inertial
from domain.models import (
    CollisionFriction,
    Inertial,
    JointDynamics,
    Link,
    RobotModel,
)
from importer.urdf_importer import import_urdf
from storage import project_storage


class PhysicsCore:
    def __init__(self, model: Optional[RobotModel] = None):
        self.model = model or RobotModel()

    def get_model(self) -> RobotModel:
        return self.model

    def load(self, model: RobotModel) -> RobotModel:
        self.model = model
        return self.model

    def import_geo_urdf(self, project_name: str) -> RobotModel:
        path = project_storage.geo_urdf_path(project_name)
        if not path.is_file():
            raise FileNotFoundError(f"Geometry URDF not found: {path}. Export from geometry editor first.")
        self.model = import_urdf(path, project_name)
        return self.model

    def find_link(self, link_id: str) -> Optional[Link]:
        return next((l for l in self.model.links if l.id == link_id), None)

    def update_inertial(self, link_id: str, inertial: Inertial) -> Link:
        link = self.find_link(link_id)
        if not link:
            raise ValueError(f"Link not found: {link_id}")
        link.inertial = inertial
        return link

    def update_friction(self, link_id: str, friction: CollisionFriction) -> Link:
        link = self.find_link(link_id)
        if not link:
            raise ValueError(f"Link not found: {link_id}")
        link.friction = friction
        return link

    def set_is_foot(self, link_id: str, is_foot: bool) -> Link:
        link = self.find_link(link_id)
        if not link:
            raise ValueError(f"Link not found: {link_id}")
        link.isFoot = is_foot
        return link

    def update_joint_dynamics(self, joint_id: str, dynamics: JointDynamics) -> None:
        joint = next((j for j in self.model.joints if j.id == joint_id), None)
        if not joint:
            raise ValueError(f"Joint not found: {joint_id}")
        joint.dynamics = dynamics

    def auto_estimate_link(self, link_id: str, density: float = 1000.0) -> Link:
        link = self.find_link(link_id)
        if not link:
            raise ValueError(f"Link not found: {link_id}")
        link.inertial = estimate_link_inertial(link, density=density)
        return link

    def auto_estimate_all(self, density: float = 1000.0) -> RobotModel:
        for link in self.model.links:
            link.inertial = estimate_link_inertial(link, density=density)
        return self.model
