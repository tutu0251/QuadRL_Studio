"""Training run registry — reads runs/ and run_info.yaml manifests."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from domain.models import RunInfo, RunStageInfo
from storage import project_storage


def _load_manifest(run_dir: Path) -> dict:
    manifest_path = run_dir / "run_info.yaml"
    if not manifest_path.is_file():
        return {}
    try:
        return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return {}


def _monitor_state(run_dir: Path) -> dict:
    state_path = run_dir / "monitor_state.yaml"
    if not state_path.is_file():
        return {}
    try:
        return yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return {}


def _list_stages(run_dir: Path) -> list[RunStageInfo]:
    stages: list[RunStageInfo] = []
    for sub in sorted(run_dir.iterdir()):
        if not sub.is_dir():
            continue
        events = list(sub.rglob("events.out.tfevents.*"))
        stages.append(
            RunStageInfo(
                name=sub.name,
                logdir=str(sub),
                has_events=bool(events),
            )
        )
    return stages


def _infer_status(run_dir: Path, monitor: dict) -> str:
    if monitor.get("status"):
        return str(monitor["status"])
    if monitor.get("pid"):
        return "running"
    return "unknown"


def describe_run(name: str, run_id: str) -> Optional[RunInfo]:
    run_dir = project_storage.runs_dir(name) / run_id
    if not run_dir.is_dir():
        return None
    manifest = _load_manifest(run_dir)
    monitor = _monitor_state(run_dir)
    return RunInfo(
        run_id=run_id,
        path=str(run_dir),
        started_at=manifest.get("started_at") or monitor.get("started_at"),
        ended_at=monitor.get("ended_at"),
        status=_infer_status(run_dir, monitor),  # type: ignore[arg-type]
        config=manifest.get("config"),
        tensorboard_logdir=manifest.get("tensorboard_logdir"),
        curriculum_enabled=bool(manifest.get("curriculum_enabled")),
        stages=_list_stages(run_dir),
        pid=monitor.get("pid"),
    )


def list_runs(name: str) -> list[RunInfo]:
    runs_root = project_storage.runs_dir(name)
    if not runs_root.is_dir():
        return []
    out: list[RunInfo] = []
    for run_dir in sorted(runs_root.iterdir(), key=lambda p: p.name, reverse=True):
        if not run_dir.is_dir() or run_dir.name.startswith("."):
            continue
        info = describe_run(name, run_dir.name)
        if info:
            out.append(info)
    return out


def write_monitor_state(name: str, run_id: str, state: dict) -> Path:
    run_dir = project_storage.runs_dir(name) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "monitor_state.yaml"
    path.write_text(yaml.dump(state, default_flow_style=False, sort_keys=False), encoding="utf-8")
    return path


def latest_run_id(name: str) -> Optional[str]:
    runs = list_runs(name)
    return runs[0].run_id if runs else None


def find_event_files(name: str, run_id: Optional[str] = None) -> list[Path]:
    runs_root = project_storage.runs_dir(name)
    if not runs_root.is_dir():
        return []
    targets: list[Path] = []
    if run_id:
        targets = [runs_root / run_id]
    else:
        targets = [p for p in runs_root.iterdir() if p.is_dir()]
    events: list[Path] = []
    for run_dir in targets:
        if run_dir.is_dir():
            events.extend(run_dir.rglob("events.out.tfevents.*"))
    return sorted(events, key=lambda p: p.stat().st_mtime, reverse=True)
