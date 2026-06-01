"""Scan and categorize editor export artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from domain.models import ExportBundle, ExportFileInfo
from storage import project_storage

CATEGORY_PREFIXES: list[tuple[str, str]] = [
    ("geometry", "geo_"),
    ("physics", "phy_"),
    ("control", "ctrl_"),
    ("sensor", "sens_"),
    ("ppo_planner", "ppo_"),
    ("rl_trainer", "rl_"),
]


def _category_for(filename: str) -> str:
    for category, prefix in CATEGORY_PREFIXES:
        if filename.startswith(prefix):
            return category
    return "other"


def _format_for(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    return ext or "unknown"


def scan_exports(name: str) -> ExportBundle:
    root = project_storage.project_dir(name)
    exports = project_storage.exports_dir(name)
    files: list[ExportFileInfo] = []

    if exports.is_dir():
        for path in sorted(exports.iterdir(), key=lambda p: p.name):
            if not path.is_file() or path.name.startswith("."):
                continue
            stat = path.stat()
            rel = str(path.relative_to(root))
            files.append(
                ExportFileInfo(
                    category=_category_for(path.name),
                    filename=path.name,
                    path=rel,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    format=_format_for(path),
                )
            )

    missing: list[str] = []
    for template in project_storage.REQUIRED_EXPORTS:
        expected = template.format(name=name)
        if not (exports / expected).is_file():
            missing.append(expected)

    sens_obs = exports / f"sens_{name}_observations.yaml"
    ctrl_gains = exports / f"ctrl_{name}_gains.yaml"
    ctrl_ctrl = exports / f"ctrl_{name}_controllers.yaml"
    sensor_exports_ready = sens_obs.is_file() and ctrl_gains.is_file() and ctrl_ctrl.is_file()
    workspace_setup = root / "workspace" / "install" / "setup.bash"
    workspace_ready = workspace_setup.is_file()
    recommended = "ros" if workspace_ready and sensor_exports_ready else "mock"

    return ExportBundle(
        project=name,
        exports_dir=str(exports),
        files=files,
        missing_required=missing,
        ready_for_training=len(missing) == 0 and sensor_exports_ready,
        workspace_ready=workspace_ready,
        sensor_exports_ready=sensor_exports_ready,
        recommended_sim_backend=recommended,
    )


def read_export_text(name: str, relative_path: str, *, max_bytes: int = 512_000) -> str:
    root = project_storage.project_dir(name)
    path = (root / relative_path).resolve()
    if project_storage.project_dir(name).resolve() not in path.parents and path != root.resolve():
        raise FileNotFoundError("Path escapes project root")
    if not path.is_file():
        raise FileNotFoundError(relative_path)
    if path.stat().st_size > max_bytes:
        data = path.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace") + "\n\n… (truncated)"
    return path.read_text(encoding="utf-8")
