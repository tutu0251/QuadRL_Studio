"""Generate and build the full colcon workspace for sensor runtime validation."""
from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from ev_ros_env import load_ros_environ
from sensor_paths import SensorProjectPaths

WG_BACKEND = Path(__file__).resolve().parents[2] / "workspace-generator" / "backend"


@contextmanager
def _with_wg_backend() -> Iterator[None]:
    ev_backend = str(Path(__file__).resolve().parent)
    wg_backend = str(WG_BACKEND)
    saved = sys.path[:]
    try:
        sys.path[:] = [p for p in sys.path if p not in {ev_backend, wg_backend}]
        sys.path.insert(0, wg_backend)
        yield
    finally:
        sys.path[:] = saved


def pipeline_exports_stale(paths: SensorProjectPaths) -> tuple[bool, list[str]]:
    with _with_wg_backend():
        from generator.manifest import exports_stale_against_workspace  # noqa: WPS433
        from paths import ProjectPaths  # noqa: WPS433

        wg_paths = ProjectPaths(paths.project_name, paths.projects_root)
        return exports_stale_against_workspace(wg_paths)


def generate_sensor_workspace(paths: SensorProjectPaths) -> dict[str, Any]:
    missing = [
        f"{stage}: {path}"
        for stage, path in paths.required_pipeline_exports()
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing pipeline exports for workspace generation — "
            + "; ".join(missing)
        )

    with _with_wg_backend():
        from generator.workspace_generator import generate_workspace  # noqa: WPS433

        return generate_workspace(paths.project_name, paths.projects_root)


def build_sensor_workspace(paths: SensorProjectPaths) -> dict[str, Any]:
    ws = paths.workspace_dir
    report: dict[str, Any] = {
        "success": False,
        "workspace_path": str(ws),
    }
    if not (ws / "src").is_dir():
        report["error"] = "workspace_not_generated"
        report["message"] = f"No workspace at {ws}; run generate first"
        return report

    env = load_ros_environ()
    proc = subprocess.run(
        ["colcon", "build", "--symlink-install"],
        cwd=str(ws),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    report["return_code"] = proc.returncode
    report["success"] = proc.returncode == 0
    report["message"] = "colcon build finished" if report["success"] else "colcon build failed"
    if not report["success"]:
        tail = "\n".join((proc.stderr or proc.stdout or "").splitlines()[-20:])
        report["log_excerpt"] = tail
    return report
