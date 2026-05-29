"""Control editor business logic."""
from __future__ import annotations

from pathlib import Path

from domain.models import (
    DEFAULT_SIM_CONTROLLER,
    ControlModel,
    JointControlConfig,
    TrainingProfile,
    new_id,
    normalize_sim_controller,
    utc_now_iso,
)
from importer.urdf_importer import import_actuated_joints
from profiles import apply_profile_a, apply_profile_b, apply_profile_c
from storage import project_storage


class ControlCore:
    def __init__(self, model: ControlModel | None = None):
        self._model = model or ControlModel()

    def get_model(self) -> ControlModel:
        return self._model

    def set_model(self, model: ControlModel) -> None:
        self._model = model

    def import_phy_urdf(self, project_name: str) -> ControlModel:
        path = project_storage.phy_urdf_path(project_name)
        if not path.is_file():
            raise FileNotFoundError(f"Physics URDF not found: {path}. Export from Physics Editor first.")

        robot_name, imported = import_actuated_joints(path)
        if not imported:
            raise ValueError("No actuated joints found in physics URDF")

        physics_map = project_storage.load_physics_joint_dynamics(project_name)
        self._model = ControlModel(
            id=new_id(),
            projectName=project_name,
            robotName=robot_name,
            sourceUrdf=str(path),
            metadata={
                "importedFrom": str(path),
                "importedAt": utc_now_iso(),
                "hasPhysicsJson": project_storage.physics_model_path(project_name).exists(),
            },
        )
        self._apply_profile(self._model.trainingProfile, imported, physics_map)
        self._model.controllerType = DEFAULT_SIM_CONTROLLER
        return self._model

    def _apply_profile(
        self,
        profile: TrainingProfile,
        imported: list | None = None,
        physics_map: dict | None = None,
    ) -> None:
        if imported is None:
            path = Path(self._model.sourceUrdf)
            if not path.is_file():
                raise FileNotFoundError("No source URDF — import phy URDF first")
            _, imported = import_actuated_joints(path)
        if physics_map is None:
            physics_map = project_storage.load_physics_joint_dynamics(self._model.projectName)

        if profile == TrainingProfile.PROFILE_A:
            apply_profile_a(self._model, imported, physics_map)
        elif profile == TrainingProfile.PROFILE_B:
            if not self._model.actuatedJoints:
                self._model.actuatedJoints = [
                    JointControlConfig(
                        name=j.name,
                        type=j.type,
                        childLinkName=j.child_link,
                        lowerLimit=j.lower_limit,
                        upperLimit=j.upper_limit,
                        effort=j.effort,
                        velocity=j.velocity,
                        enabled=False,
                    )
                    for j in imported
                ]
            apply_profile_b(self._model)
        elif profile == TrainingProfile.PROFILE_C:
            if not self._model.actuatedJoints:
                self._model.actuatedJoints = [
                    JointControlConfig(
                        name=j.name,
                        type=j.type,
                        childLinkName=j.child_link,
                        lowerLimit=j.lower_limit,
                        upperLimit=j.upper_limit,
                        effort=j.effort,
                        velocity=j.velocity,
                        enabled=False,
                    )
                    for j in imported
                ]
            apply_profile_c(self._model)

    def set_profile(self, profile: TrainingProfile) -> ControlModel:
        self._model.trainingProfile = profile
        self._apply_profile(profile)
        return self._model

    def regenerate(self) -> ControlModel:
        self._apply_profile(self._model.trainingProfile)
        return self._model

    def update_joint(self, joint_name: str, updates: dict) -> ControlModel:
        for j in self._model.actuatedJoints:
            if j.name == joint_name:
                for k, v in updates.items():
                    if hasattr(j, k):
                        setattr(j, k, v)
                return self._model
        raise KeyError(f"Joint not found: {joint_name}")
