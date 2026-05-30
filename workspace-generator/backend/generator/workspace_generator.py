"""Generate colcon workspace from QuadRL editor exports."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import yaml

from generator.bridge_args import bridge_to_ros_gz_config, load_bridge_doc
from generator.manifest import build_manifest
from generator.urdf_patch import patch_bridge_yaml, patch_contact_sensors, patch_controllers_parameters
from paths import ProjectPaths

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
WORLD_NAME = "flat"


def export_robot_sdf(urdf_path: Path, sdf_path: Path) -> None:
    proc = subprocess.run(
        ["ign", "sdf", "-p", str(urdf_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ign sdf failed for {urdf_path}: {proc.stderr or proc.stdout}")
    sdf_path.write_text(proc.stdout, encoding="utf-8")


class WorkspaceGenerator:
    def __init__(self, paths: ProjectPaths):
        self._paths = paths
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            keep_trailing_newline=True,
        )

    def generate(self) -> dict:
        manifest = build_manifest(self._paths)
        if not manifest.valid:
            raise FileNotFoundError("; ".join(manifest.errors))

        ws = self._paths.workspace_dir
        desc = self._paths.description_src()
        bringup = self._paths.bringup_src()

        if ws.exists():
            shutil.rmtree(ws / "src", ignore_errors=True)
        (ws / "src").mkdir(parents=True, exist_ok=True)
        desc.mkdir(parents=True, exist_ok=True)
        bringup.mkdir(parents=True, exist_ok=True)

        controllers_name = self._paths.controllers_yaml().name
        urdf_text = self._paths.sens_rl_urdf().read_text(encoding="utf-8")
        urdf_text = patch_controllers_parameters(urdf_text, controllers_name)
        urdf_text = patch_contact_sensors(urdf_text)

        (desc / "urdf").mkdir(parents=True, exist_ok=True)
        (desc / "config").mkdir(parents=True, exist_ok=True)
        (desc / "urdf" / "robot.urdf").write_text(urdf_text, encoding="utf-8")
        export_robot_sdf(desc / "urdf" / "robot.urdf", desc / "urdf" / "robot.sdf")

        # gz_ros2_control resolves <parameters> relative to the URDF directory.
        shutil.copy2(self._paths.controllers_yaml(), desc / "urdf" / controllers_name)
        shutil.copy2(self._paths.controllers_yaml(), desc / "config" / controllers_name)
        shutil.copy2(self._paths.gains_yaml(), desc / "config" / self._paths.gains_yaml().name)
        bridge_name = self._paths.bridge_yaml().name
        bridge_text = self._paths.bridge_yaml().read_text(encoding="utf-8")
        bridge_text = patch_bridge_yaml(bridge_text, urdf_text, WORLD_NAME)
        (desc / "config" / bridge_name).write_text(bridge_text, encoding="utf-8")
        shutil.copy2(
            self._paths.observations_yaml(),
            desc / "config" / self._paths.observations_yaml().name,
        )

        ctx = {
            "project_name": self._paths.project_name,
            "description_pkg": self._paths.description_pkg,
            "bringup_pkg": self._paths.bringup_pkg,
        }
        (desc / "package.xml").write_text(
            self._env.get_template("description_package.xml.j2").render(**ctx),
            encoding="utf-8",
        )
        (desc / "CMakeLists.txt").write_text(
            self._env.get_template("description_CMakeLists.txt.j2").render(**ctx),
            encoding="utf-8",
        )

        bridge_doc = load_bridge_doc(desc / "config" / bridge_name)
        ros_gz_bridge_path = desc / "config" / "ros_gz_bridge.yaml"
        ros_gz_bridge_path.write_text(
            yaml.dump(bridge_to_ros_gz_config(bridge_doc, WORLD_NAME), default_flow_style=False),
            encoding="utf-8",
        )
        launch_ctx = {
            **ctx,
            "bridge_config_relpath": "config/ros_gz_bridge.yaml",
            "controllers_basename": controllers_name,
        }

        (bringup / "launch").mkdir(parents=True, exist_ok=True)
        (bringup / "worlds").mkdir(parents=True, exist_ok=True)
        (bringup / "resource").mkdir(parents=True, exist_ok=True)
        (bringup / "resource" / self._paths.bringup_pkg).write_text("", encoding="utf-8")
        (bringup / self._paths.bringup_pkg).mkdir(parents=True, exist_ok=True)
        (bringup / self._paths.bringup_pkg / "__init__.py").write_text("", encoding="utf-8")

        shutil.copy2(TEMPLATES_DIR / "flat.world", bringup / "worlds" / "flat.world")
        (bringup / "package.xml").write_text(
            self._env.get_template("bringup_package.xml.j2").render(**ctx),
            encoding="utf-8",
        )
        (bringup / "setup.py").write_text(
            self._env.get_template("bringup_setup.py.j2").render(**ctx),
            encoding="utf-8",
        )
        (bringup / "setup.cfg").write_text(
            self._env.get_template("bringup_setup.cfg.j2").render(**ctx),
            encoding="utf-8",
        )
        (bringup / "launch" / "sim.launch.py").write_text(
            self._env.get_template("sim.launch.py.j2").render(**launch_ctx),
            encoding="utf-8",
        )
        (bringup / "launch" / "training_readiness.launch.py").write_text(
            self._env.get_template("training_readiness.launch.py.j2").render(**launch_ctx),
            encoding="utf-8",
        )

        manifest_doc = {
            "version": "1.0",
            "project_name": self._paths.project_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "world_name": WORLD_NAME,
            "packages": {
                "description": self._paths.description_pkg,
                "bringup": self._paths.bringup_pkg,
            },
            "manifest": manifest.to_dict(),
        }
        self._paths.manifest_path.write_text(
            json.dumps(manifest_doc, indent=2),
            encoding="utf-8",
        )

        return {
            "generated": True,
            "workspace_path": str(ws),
            "description_pkg": self._paths.description_pkg,
            "bringup_pkg": self._paths.bringup_pkg,
            "manifest_path": str(self._paths.manifest_path),
        }


def generate_workspace(project_name: str, projects_root: Path | None = None) -> dict:
    paths = ProjectPaths(project_name, projects_root) if projects_root else ProjectPaths(project_name)
    return WorkspaceGenerator(paths).generate()
