"""Orchestrate full RL package export."""
from __future__ import annotations

from pathlib import Path

from domain.models import SensorModel
from exporter.bridge_exporter import export_bridge_yaml
from exporter.observations_exporter import export_observations_yaml
from exporter.sdf_exporter import SdfConversionError, export_sdf_from_urdf
from exporter.sensor_urdf_exporter import merge_sensors_into_urdf
from storage import project_storage


def export_all(model: SensorModel, project_name: str) -> dict[str, str]:
    ctrl_path = project_storage.ctrl_urdf_path(project_name)
    if not ctrl_path.is_file():
        raise FileNotFoundError(f"Missing control URDF: {ctrl_path}")

    urdf_out = project_storage.export_rl_urdf_path(project_name)
    sdf_out = project_storage.export_sdf_path(project_name)
    bridge_out = project_storage.export_bridge_yaml_path(project_name)
    obs_out = project_storage.export_observations_yaml_path(project_name)

    merge_sensors_into_urdf(model, ctrl_path, urdf_out)

    sdf_written = ""
    try:
        export_sdf_from_urdf(urdf_out, sdf_out)
        sdf_written = str(sdf_out)
    except SdfConversionError as e:
        sdf_written = f"skipped: {e}"

    export_bridge_yaml(model, bridge_out)
    export_observations_yaml(
        model,
        obs_out,
        controllers_rel=f"ctrl_{project_name}_controllers.yaml",
        gains_rel=f"ctrl_{project_name}_gains.yaml",
    )

    result = {
        "urdf": str(urdf_out),
        "bridge": str(bridge_out),
        "observations": str(obs_out),
    }
    if sdf_written and not sdf_written.startswith("skipped"):
        result["sdf"] = sdf_written
    elif sdf_written:
        result["sdf_note"] = sdf_written
    return result
