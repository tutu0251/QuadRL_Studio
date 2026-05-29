"""Physics validation — blocks export on errors."""
from __future__ import annotations

import math

from domain.estimate import estimate_link_inertial
from domain.inertia_math import is_positive_definite, satisfies_triangle_inequalities
from domain.models import RobotModel, ValidationIssue, ValidationResult


class PhysicsValidator:
    def __init__(self, model: RobotModel):
        self.model = model
        self.errors: list[ValidationIssue] = []
        self.warnings: list[ValidationIssue] = []

    def validate(self) -> ValidationResult:
        self.errors.clear()
        self.warnings.clear()
        if not self.model.links:
            self._error("no_links", "Robot has no links")
        for link in self.model.links:
            self._check_inertial(link)
            self._check_friction(link)
        for joint in self.model.joints:
            self._check_joint(joint)
        self._check_foot_friction()
        return ValidationResult(valid=len(self.errors) == 0, errors=self.errors, warnings=self.warnings)

    def _error(self, code: str, message: str, entity_type: str | None = None, entity_id: str | None = None):
        self.errors.append(
            ValidationIssue(severity="error", code=code, message=message, entityType=entity_type, entityId=entity_id)
        )

    def _warn(self, code: str, message: str, entity_type: str | None = None, entity_id: str | None = None):
        self.warnings.append(
            ValidationIssue(severity="warning", code=code, message=message, entityType=entity_type, entityId=entity_id)
        )

    def _check_inertial(self, link):
        ins = link.inertial
        if ins.mass <= 0:
            self._error("invalid_mass", f"Link '{link.name}' mass must be > 0", "link", link.id)
        if ins.mass == 1.0:
            self._warn("placeholder_mass", f"Link '{link.name}' uses default mass=1.0", "link", link.id)
        if not is_positive_definite(ins.ixx, ins.ixy, ins.ixz, ins.iyy, ins.iyz, ins.izz):
            self._error("inertia_not_pd", f"Link '{link.name}' inertia matrix is not positive definite", "link", link.id)
        if not satisfies_triangle_inequalities(ins.ixx, ins.iyy, ins.izz):
            self._warn("inertia_triangle", f"Link '{link.name}' principal moments may violate triangle inequalities", "link", link.id)
        self._check_com_in_bounds(link)

    def _check_com_in_bounds(self, link):
        if not link.shapes:
            return
        est = estimate_link_inertial(link, density=1.0)
        # bounds from shape AABB in link frame
        max_ext = 0.0
        for s in link.shapes:
            d = s.dimensions
            if s.type.value == "box":
                max_ext = max(max_ext, max(d[0], d[1], d[2]) / 2)
            elif s.type.value == "sphere":
                max_ext = max(max_ext, d[0])
            else:
                max_ext = max(max_ext, max(d[0], d[1] if len(d) > 1 else d[0]))
        com = link.inertial.com
        dist = math.sqrt(com.x**2 + com.y**2 + com.z**2)
        if dist > max_ext * 2.5 + 0.05:
            self._warn(
                "com_outside_geometry",
                f"Link '{link.name}' COM is far from shape bounds (dist={dist:.3f}m)",
                "link",
                link.id,
            )

    def _check_friction(self, link):
        fr = link.friction
        if not fr.enabled:
            return
        if fr.useMu and fr.mu < 0:
            self._error("negative_friction", f"Link '{link.name}' μ₁ must be >= 0", "link", link.id)
        if fr.useMu2 and fr.mu2 < 0:
            self._error("negative_friction", f"Link '{link.name}' μ₂ must be >= 0", "link", link.id)

    def _check_joint(self, joint):
        d = joint.dynamics
        if d.effort <= 0:
            self._error("invalid_effort", f"Joint '{joint.name}' effort must be > 0", "joint", joint.id)
        if d.velocity <= 0 and joint.type.value in ("revolute", "prismatic"):
            self._warn("low_velocity_limit", f"Joint '{joint.name}' velocity limit is very low", "joint", joint.id)

    def _check_foot_friction(self):
        feet = [l for l in self.model.links if l.isFoot]
        if not feet:
            self._warn("no_foot_links", "No foot links marked (name contains foot/toe/pad or isFoot flag)")
            return
        for foot in feet:
            fr = foot.friction
            if not fr.enabled:
                self._warn(
                    "foot_friction_disabled",
                    f"Foot link '{foot.name}' has collision friction disabled",
                    "link",
                    foot.id,
                )
                continue
            mu_active = fr.useMu or fr.useMu2
            mu_bad = (fr.useMu and fr.mu <= 0.01) or (fr.useMu2 and fr.mu2 <= 0.01)
            if mu_active and mu_bad:
                self._error(
                    "missing_foot_friction",
                    f"Foot link '{foot.name}' has near-zero friction (enabled μ)",
                    "link",
                    foot.id,
                )
            elif not mu_active:
                self._warn(
                    "foot_friction_ignored",
                    f"Foot link '{foot.name}' has no μ₁/μ₂ enabled",
                    "link",
                    foot.id,
                )
