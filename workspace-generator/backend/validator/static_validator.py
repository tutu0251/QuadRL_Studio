"""Static training readiness checks (no ROS runtime)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import yaml

from generator.bridge_args import load_bridge_doc, observation_topics
from generator.manifest import build_manifest, exports_stale_against_workspace
from paths import ProjectPaths
from validator.sensor_export_validator import validate_sensor_exports


def _load_observations(path):
    text = path.read_text(encoding="utf-8")
    if text.startswith("#"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    doc = yaml.safe_load(text) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"Invalid observations YAML: {path}")
    return doc


def validate_static(paths: ProjectPaths) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    manifest = build_manifest(paths)
    if not manifest.valid:
        errors.extend(manifest.errors)

    sensor_report = validate_sensor_exports(paths)
    errors.extend(sensor_report.get("errors") or [])
    warnings.extend(sensor_report.get("warnings") or [])

    if not paths.bridge_yaml().is_file() or not paths.observations_yaml().is_file():
        return {
            "valid": False,
            "errors": errors or ["Missing bridge or observations export"],
            "warnings": warnings,
            "sensor_exports": sensor_report,
        }

    bridge_doc = load_bridge_doc(paths.bridge_yaml())
    obs_doc = _load_observations(paths.observations_yaml())
    bridge_ros_topics = {
        str(e.get("ros_topic_name"))
        for e in (bridge_doc.get("bridge") or [])
        if e.get("ros_topic_name")
    }
    for topic in observation_topics(obs_doc):
        if topic not in bridge_ros_topics:
            errors.append(f"Observation topic not in bridge config: {topic}")

    if paths.sens_rl_urdf().is_file() and paths.controllers_yaml().is_file():
        try:
            root = ET.parse(paths.sens_rl_urdf()).getroot()
            urdf_joints = {
                j.get("name")
                for j in root.findall("joint")
                if j.get("type") not in ("fixed", None)
            }
            ctrl_doc = yaml.safe_load(paths.controllers_yaml().read_text(encoding="utf-8")) or {}
            jtc = ctrl_doc.get("joint_trajectory_controller") or {}
            ctrl_joints = set((jtc.get("ros__parameters") or {}).get("joints") or [])
            missing = ctrl_joints - urdf_joints
            if missing:
                errors.append(f"Controller joints missing from URDF: {sorted(missing)}")
        except (ET.ParseError, yaml.YAMLError) as exc:
            errors.append(f"Failed to cross-check URDF/controllers: {exc}")

    stale, changed = exports_stale_against_workspace(paths)
    if stale:
        label = ", ".join(changed) if changed else "workspace missing"
        warnings.append(f"Workspace out of sync with exports ({label}); will regenerate before build")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "manifest": manifest.to_dict(),
        "sensor_exports": sensor_report,
        "observation_topic_count": len(observation_topics(obs_doc)),
        "workspace_stale": stale,
        "workspace_stale_files": changed,
    }
