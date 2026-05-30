"""Export manifest and pipeline readiness checks."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from paths import ProjectPaths


@dataclass
class ManifestEntry:
    stage: str
    path: Path
    required: bool = True

    def exists(self) -> bool:
        return self.path.is_file()

    def sha256(self) -> str | None:
        if not self.exists():
            return None
        h = hashlib.sha256()
        h.update(self.path.read_bytes())
        return h.hexdigest()


@dataclass
class ManifestResult:
    valid: bool
    entries: list[ManifestEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "files": [
                {
                    "stage": e.stage,
                    "path": str(e.path),
                    "exists": e.exists(),
                    "sha256": e.sha256(),
                }
                for e in self.entries
            ],
        }


def build_manifest(paths: ProjectPaths) -> ManifestResult:
    entries = [
        ManifestEntry("geometry", paths.geo_urdf()),
        ManifestEntry("physics", paths.phy_urdf()),
        ManifestEntry("control", paths.ctrl_urdf()),
        ManifestEntry("control", paths.controllers_yaml()),
        ManifestEntry("control", paths.gains_yaml()),
        ManifestEntry("sensor", paths.sens_rl_urdf()),
        ManifestEntry("sensor", paths.bridge_yaml()),
        ManifestEntry("sensor", paths.observations_yaml()),
        ManifestEntry("sensor", paths.sens_sdf(), required=False),
        ManifestEntry("trainer", paths.rl_config_yaml(), required=False),
    ]
    errors: list[str] = []
    for entry in entries:
        if entry.required and not entry.exists():
            errors.append(f"Missing {entry.stage} export: {entry.path}")
    return ManifestResult(valid=len(errors) == 0, entries=entries, errors=errors)


def exports_stale_against_workspace(paths: ProjectPaths) -> tuple[bool, list[str]]:
    """Compare export file hashes to workspace_manifest.json; detect drift after re-export."""
    manifest_path = paths.manifest_path
    if not manifest_path.is_file():
        return True, ["workspace not generated"]

    try:
        ws_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, ["invalid workspace_manifest.json"]

    saved_hashes = {
        str(item.get("path")): item.get("sha256")
        for item in (ws_doc.get("manifest") or {}).get("files") or []
        if item.get("path")
    }

    changed: list[str] = []
    for entry in build_manifest(paths).entries:
        path_str = str(entry.path)
        current_hash = entry.sha256()
        if saved_hashes.get(path_str) != current_hash:
            changed.append(entry.path.name)

    return len(changed) > 0, changed
