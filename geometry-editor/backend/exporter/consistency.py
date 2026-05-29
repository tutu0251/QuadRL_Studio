"""Cross-format export consistency checks."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from domain.models import RobotModel, ValidationIssue


def check_export_consistency(model: RobotModel, urdf_path: Path, sdf_path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    expected_links = {l.name for l in model.links}
    expected_joints = {j.name for j in model.joints}

    if urdf_path.exists():
        urdf_root = ET.parse(urdf_path).getroot()
        for link_el in urdf_root.findall("link"):
            for geom_parent in link_el.findall("visual/geometry") + link_el.findall("collision/geometry"):
                box = geom_parent.find("box")
                if box is not None and not box.get("size"):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="urdf_box_format",
                            message=f"URDF box on {link_el.get('name')} missing size= attribute (SDF-style XML)",
                        )
                    )
                cyl = geom_parent.find("cylinder")
                if cyl is not None and (not cyl.get("radius") or not cyl.get("length")):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="urdf_cylinder_format",
                            message=f"URDF cylinder on {link_el.get('name')} missing radius=/length= attributes",
                        )
                    )
                sph = geom_parent.find("sphere")
                if sph is not None and not sph.get("radius"):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="urdf_sphere_format",
                            message=f"URDF sphere on {link_el.get('name')} missing radius= attribute",
                        )
                    )
        urdf_links = {el.get("name") for el in urdf_root.findall("link")}
        urdf_joints = {el.get("name") for el in urdf_root.findall("joint")}
        if urdf_links != expected_links:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="urdf_link_mismatch",
                    message=f"URDF links {urdf_links} != model {expected_links}",
                )
            )
        if urdf_joints != expected_joints:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="urdf_joint_mismatch",
                    message=f"URDF joints {urdf_joints} != model {expected_joints}",
                )
            )

    if sdf_path.exists():
        sdf_root = ET.parse(sdf_path).getroot()
        model_el = sdf_root.find("model")
        if model_el is not None:
            for link_el in model_el.findall("link"):
                for tag in ("visual", "collision"):
                    for vc in link_el.findall(tag):
                        if not vc.get("name"):
                            issues.append(
                                ValidationIssue(
                                    severity="error",
                                    code="sdf_missing_geom_name",
                                    message=f"SDF {tag} on {link_el.get('name')} missing required name= attribute",
                                )
                            )
            # SDF is produced from URDF via gz/ign; fixed joints may be lumped, so do not
            # require a 1:1 link/joint set match with the editor model.

    return issues
