"""Path helpers for control export runtime validation."""
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
class ControlProjectPaths:
    project_name: str
    exports_dir: Path
    projects_root: Path = PROJECTS_ROOT

    @property
    def project_dir(self) -> Path:
        return self.projects_root / self.project_name

    @property
    def workspace_dir(self) -> Path:
        return self.project_dir / "workspace_control"

    @property
    def manifest_path(self) -> Path:
        return self.workspace_dir / "control_manifest.json"

    @property
    def pkg_prefix(self) -> str:
        return sanitize_package_name(self.project_name)

    @property
    def description_pkg(self) -> str:
        return f"{self.pkg_prefix}_description"

    @property
    def bringup_pkg(self) -> str:
        return f"{self.pkg_prefix}_bringup"

    def ctrl_urdf(self) -> Path:
        return self.exports_dir / f"ctrl_{self.project_name}_ros2_control.urdf"

    def controllers_yaml(self) -> Path:
        return self.exports_dir / f"ctrl_{self.project_name}_controllers.yaml"

    def gains_yaml(self) -> Path:
        return self.exports_dir / f"ctrl_{self.project_name}_gains.yaml"

    def description_src(self) -> Path:
        return self.workspace_dir / "src" / self.description_pkg

    def bringup_src(self) -> Path:
        return self.workspace_dir / "src" / self.bringup_pkg

    def install_setup(self) -> Path:
        return self.workspace_dir / "install" / "setup.bash"

    @classmethod
    def from_exports(cls, exports_dir: Path, project_name: str) -> ControlProjectPaths:
        exports = exports_dir.expanduser().resolve()
        if exports.name == "exports" and exports.parent.name == project_name:
            return cls(project_name=project_name, exports_dir=exports, projects_root=exports.parent.parent)
        return cls(project_name=project_name, exports_dir=exports)
