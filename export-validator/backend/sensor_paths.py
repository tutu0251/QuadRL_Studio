"""Path helpers for sensor export runtime validation."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

PROJECTS_ROOT = Path(
    os.environ.get("QUADRL_PROJECTS_DIR", Path.home() / "quadruped_dev_tool" / "projects")
).expanduser().resolve()

_PKG_NAME_RE = re.compile(r"[^a-z0-9_]")


def sanitize_package_name(project_name: str) -> str:
    name = project_name.lower().strip()
    name = _PKG_NAME_RE.sub("_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name or name[0].isdigit():
        name = f"robot_{name or 'unnamed'}"
    return name


@dataclass(frozen=True)
class SensorProjectPaths:
    project_name: str
    exports_dir: Path
    projects_root: Path = PROJECTS_ROOT

    @property
    def project_dir(self) -> Path:
        return self.projects_root / self.project_name

    @property
    def workspace_dir(self) -> Path:
        return self.project_dir / "workspace"

    @property
    def manifest_path(self) -> Path:
        return self.workspace_dir / "workspace_manifest.json"

    @property
    def pkg_prefix(self) -> str:
        return sanitize_package_name(self.project_name)

    @property
    def description_pkg(self) -> str:
        return f"{self.pkg_prefix}_description"

    @property
    def bringup_pkg(self) -> str:
        return f"{self.pkg_prefix}_bringup"

    def geo_urdf(self) -> Path:
        return self.exports_dir / f"geo_{self.project_name}.urdf"

    def phy_urdf(self) -> Path:
        return self.exports_dir / f"phy_{self.project_name}.urdf"

    def ctrl_urdf(self) -> Path:
        return self.exports_dir / f"ctrl_{self.project_name}_ros2_control.urdf"

    def controllers_yaml(self) -> Path:
        return self.exports_dir / f"ctrl_{self.project_name}_controllers.yaml"

    def gains_yaml(self) -> Path:
        return self.exports_dir / f"ctrl_{self.project_name}_gains.yaml"

    def sens_rl_urdf(self) -> Path:
        return self.exports_dir / f"sens_{self.project_name}_rl.urdf"

    def bridge_yaml(self) -> Path:
        return self.exports_dir / f"sens_{self.project_name}_bridge.yaml"

    def observations_yaml(self) -> Path:
        return self.exports_dir / f"sens_{self.project_name}_observations.yaml"

    def description_src(self) -> Path:
        return self.workspace_dir / "src" / self.description_pkg

    def bringup_src(self) -> Path:
        return self.workspace_dir / "src" / self.bringup_pkg

    def install_setup(self) -> Path:
        return self.workspace_dir / "install" / "setup.bash"

    @classmethod
    def from_exports(cls, exports_dir: Path, project_name: str) -> SensorProjectPaths:
        exports = exports_dir.expanduser().resolve()
        if exports.name == "exports" and exports.parent.name == project_name:
            return cls(project_name=project_name, exports_dir=exports, projects_root=exports.parent.parent)
        return cls(project_name=project_name, exports_dir=exports)

    def required_sensor_exports(self) -> list[Path]:
        return [self.sens_rl_urdf(), self.bridge_yaml(), self.observations_yaml()]

    def required_pipeline_exports(self) -> list[tuple[str, Path]]:
        return [
            ("geometry", self.geo_urdf()),
            ("physics", self.phy_urdf()),
            ("control", self.ctrl_urdf()),
            ("control", self.controllers_yaml()),
            ("control", self.gains_yaml()),
            ("sensor", self.sens_rl_urdf()),
            ("sensor", self.bridge_yaml()),
            ("sensor", self.observations_yaml()),
        ]
