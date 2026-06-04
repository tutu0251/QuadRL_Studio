"""Train Monitor project-local persistence (confirmations, timing)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from storage import project_storage

DEFAULT_CONTROLLER_DELAY_S = 25.0


def monitor_yaml_path(name: str) -> Path:
    return project_storage.exports_dir(name) / f"tm_{name}_monitor.yaml"


def default_pose_path(name: str) -> Path:
    return project_storage.exports_dir(name) / f"geo_{name}_default_pose.yaml"


def gains_path(name: str) -> Path:
    return project_storage.exports_dir(name) / f"ctrl_{name}_gains.yaml"


def observations_path(name: str) -> Path:
    return project_storage.exports_dir(name) / f"sens_{name}_observations.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    doc = yaml.safe_load(body) or {}
    return doc if isinstance(doc, dict) else {}


def _dump_yaml(path: Path, doc: dict[str, Any], header: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + yaml.dump(doc, default_flow_style=False, sort_keys=False), encoding="utf-8")


def load_monitor_doc(name: str) -> dict[str, Any]:
    return _load_yaml(monitor_yaml_path(name))


def save_monitor_doc(name: str, doc: dict[str, Any]) -> None:
    header = "# Train Monitor — topic confirmations and UI state\n"
    _dump_yaml(monitor_yaml_path(name), doc, header)


def confirmed_topics(name: str) -> list[str]:
    doc = load_monitor_doc(name)
    raw = doc.get("confirmed_topics") or []
    return [str(t) for t in raw if t]


def set_confirmed_topics(name: str, topics: list[str]) -> None:
    doc = load_monitor_doc(name)
    doc["confirmed_topics"] = sorted(set(topics))
    save_monitor_doc(name, doc)


def load_pose_doc(name: str) -> dict[str, Any]:
    return _load_yaml(default_pose_path(name))


def save_pose_doc(name: str, doc: dict[str, Any]) -> None:
    header = "# Default spawn / reset pose (Train Monitor may add spawn_offset and timing)\n"
    _dump_yaml(default_pose_path(name), doc, header)
