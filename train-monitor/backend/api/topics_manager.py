"""Topic listing and confirmation for Train Monitor."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

from api.command_builder import build_topic_echo_command, build_topics_confirm_command
from domain.models import TopicEntry, TopicsBundle
from storage import monitor_storage, project_storage

REPO_ROOT = Path(__file__).resolve().parents[3]
WS_BACKEND = REPO_ROOT / "workspace-generator" / "backend"
if str(WS_BACKEND) not in sys.path:
    sys.path.insert(0, str(WS_BACKEND))


def _load_observations(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    doc = yaml.safe_load(body) or {}
    return doc if isinstance(doc, dict) else {}


def _runtime_topics(name: str) -> dict[str, str]:
    report_path = project_storage.project_dir(name) / "workspace" / "readiness_report.json"
    if not report_path.is_file():
        return {}
    try:
        doc = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    phases = doc.get("phases") or {}
    runtime = phases.get("runtime") or {}
    raw = runtime.get("topics") or {}
    return {str(k): str(v) for k, v in raw.items()}


def _bridge_topics(name: str) -> set[str]:
    try:
        from paths import ProjectPaths

        paths = ProjectPaths(name, project_storage.PROJECTS_ROOT)
        if not paths.bridge_yaml().is_file():
            return set()
        from generator.bridge_args import load_bridge_doc

        bridge_doc = load_bridge_doc(paths.bridge_yaml())
        return {
            str(e.get("ros_topic_name"))
            for e in (bridge_doc.get("bridge") or [])
            if e.get("ros_topic_name")
        }
    except Exception:
        return set()


def _setup_bash(name: str) -> Optional[str]:
    setup = project_storage.project_dir(name) / "workspace" / "install" / "setup.bash"
    return str(setup) if setup.is_file() else None


def list_topics(name: str) -> TopicsBundle:
    obs_path = monitor_storage.observations_path(name)
    obs_doc = _load_observations(obs_path)
    observations = obs_doc.get("observations") or {}
    bridge = _bridge_topics(name)
    runtime = _runtime_topics(name)
    confirmed = set(monitor_storage.confirmed_topics(name))
    setup = _setup_bash(name)

    entries: list[TopicEntry] = []
    for key, spec in observations.items():
        if not isinstance(spec, dict):
            continue
        topic = str(spec.get("topic", ""))
        kind = str(spec.get("kind", "contact"))
        runtime_status = runtime.get(topic)
        if runtime_status is None:
            runtime_status = "pending"
        elif runtime_status == "ok":
            runtime_status = "ok"
        else:
            runtime_status = "failed"
        entries.append(
            TopicEntry(
                key=str(key),
                topic=topic,
                kind=kind,
                bridge_present=topic in bridge if topic else False,
                runtime_status=runtime_status,
                runtime_detail=runtime.get(topic) if topic in runtime else None,
                confirmed=topic in confirmed if topic else False,
                echo_command=build_topic_echo_command(topic, setup_bash=setup) if topic else "",
            )
        )

    entries.sort(key=lambda e: e.topic)
    return TopicsBundle(
        project=name,
        topics=entries,
        confirmed_topics=sorted(confirmed),
        bridge_topic_count=len(bridge),
        observations_path=str(obs_path.relative_to(project_storage.project_dir(name)))
        if obs_path.is_file()
        else f"exports/sens_{name}_observations.yaml",
    )


def update_confirmations(name: str, topics: list[str]) -> tuple[TopicsBundle, str]:
    monitor_storage.set_confirmed_topics(name, topics)
    bundle = list_topics(name)
    command = build_topics_confirm_command(name, bundle.confirmed_topics)
    return bundle, command
