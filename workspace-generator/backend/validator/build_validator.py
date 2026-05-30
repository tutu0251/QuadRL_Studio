"""Colcon build wrapper."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import ProjectPaths
from ros_env import load_ros_environ


def build_workspace(paths: ProjectPaths, *, clean_first: bool = False) -> dict[str, Any]:
    ws = paths.workspace_dir
    report: dict[str, Any] = {
        "success": False,
        "workspace_path": str(ws),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "logs": [],
    }

    if not (ws / "src").is_dir():
        report["error"] = "workspace_not_generated"
        report["message"] = f"No workspace at {ws}; run generate first"
        return report

    if not shutil.which("colcon"):
        report["error"] = "colcon_missing"
        report["message"] = "colcon not found in PATH"
        return report

    env = load_ros_environ()
    if clean_first:
        clean = subprocess.run(
            ["colcon", "clean", "workspace", "-y"],
            cwd=str(ws),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        report["logs"].extend((clean.stdout or "").splitlines())
        report["logs"].extend((clean.stderr or "").splitlines())

    proc = subprocess.run(
        ["colcon", "build", "--symlink-install"],
        cwd=str(ws),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    report["logs"].extend((proc.stdout or "").splitlines())
    report["logs"].extend((proc.stderr or "").splitlines())
    report["return_code"] = proc.returncode
    report["success"] = proc.returncode == 0
    report["message"] = "colcon build finished" if report["success"] else "colcon build failed"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    return report


def write_build_report(paths: ProjectPaths, report: dict[str, Any]) -> Path:
    paths.workspace_dir.mkdir(parents=True, exist_ok=True)
    out = paths.workspace_dir / "build_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
