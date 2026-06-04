"""Poll observation topics with ros2 topic echo while sim is running."""
from __future__ import annotations

import shlex
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from api.topics_manager import list_topics
from storage import project_storage

REPO_ROOT = Path(__file__).resolve().parents[3]
EV_BACKEND = REPO_ROOT / "export-validator" / "backend"
TRAINING_DIR = REPO_ROOT / "training"
if str(EV_BACKEND) not in sys.path:
    sys.path.insert(0, str(EV_BACKEND))
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

EchoCallback = Callable[[str, dict[str, Any]], None]
ECHO_SNIPPET_LEN = 240
ECHO_TEXT_MAX = 4000
ROUND_INTERVAL_S = 2.0


class TopicEchoManager:
    def __init__(self) -> None:
        self._state: str = "idle"
        self._project: Optional[str] = None
        self._topics: list[str] = []
        self._latest: dict[str, dict[str, Any]] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[EchoCallback] = []

    def subscribe(self, callback: EchoCallback) -> None:
        self._callbacks.append(callback)

    def unsubscribe(self, callback: EchoCallback) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def is_running(self) -> bool:
        return self._state == "running"

    def get_latest(self, project: Optional[str] = None) -> dict[str, dict[str, Any]]:
        if project and self._project and project != self._project:
            return {}
        return dict(self._latest)

    def get_status(self, project: Optional[str] = None) -> dict[str, Any]:
        if project and self._project and project != self._project:
            return {
                "project": project,
                "state": "idle",
                "topics": [],
                "latest": {},
            }
        return {
            "project": self._project or project or "",
            "state": self._state,
            "topics": list(self._topics),
            "latest": dict(self._latest),
        }

    def _setup_path(self, project: str) -> Path:
        from api.spawn_workspace_session import require_workspace_setup

        return require_workspace_setup(project)

    def _ros_env(self, setup: Path) -> dict[str, str]:
        from quadrl_env.ros_env import load_ros_environ

        return load_ros_environ(workspace_setup=setup)

    def _echo_once(self, topic: str, setup: Path, env: dict[str, str]) -> tuple[bool, str]:
        from ev_ros_env import bash_ros_cmd

        quoted = shlex.quote(topic)
        script = (
            f"ros2 topic echo {quoted} --once --spin-time 8 --qos-reliability reliable"
        )
        proc = bash_ros_cmd(script, setup=setup, timeout=18.0, env=env)
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        if proc.returncode == 0 and out and "---" in out:
            return True, out[:ECHO_TEXT_MAX]
        if "average rate" in out:
            return True, out[:ECHO_TEXT_MAX]
        return False, out[-ECHO_TEXT_MAX:] if out else "no messages"

    def _publish(self, topic: str, ok: bool, text: str) -> None:
        snippet = text.strip().replace("\r\n", "\n")
        if len(snippet) > ECHO_SNIPPET_LEN:
            snippet = snippet[:ECHO_SNIPPET_LEN] + "…"
        entry = {
            "ok": ok,
            "snippet": snippet,
            "text": text[:ECHO_TEXT_MAX],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._latest[topic] = entry
        for cb in self._callbacks:
            try:
                cb(topic, entry)
            except Exception:
                pass

    def _run_loop(self, project: str) -> None:
        try:
            setup = self._setup_path(project)
            env = self._ros_env(setup)
        except Exception as exc:
            self._publish("(watch)", False, str(exc))
            return

        while not self._stop_event.is_set():
            for topic in self._topics:
                if self._stop_event.is_set():
                    break
                ok, text = self._echo_once(topic, setup, env)
                self._publish(topic, ok, text)
            self._stop_event.wait(ROUND_INTERVAL_S)

    def start(self, project: str, topics: Optional[list[str]] = None) -> dict[str, Any]:
        if topics is None:
            bundle = list_topics(project)
            topics = [t.topic for t in bundle.topics if t.topic]
        topics = [t for t in dict.fromkeys(topics) if t]

        if self.is_running() and self._project == project:
            self._topics = topics
            return self.get_status(project)

        self.stop(project)

        self._project = project
        self._topics = topics
        self._latest = {}
        self._state = "running"
        self._stop_event.clear()

        def _worker() -> None:
            try:
                self._run_loop(project)
            finally:
                self._state = "idle"

        self._thread = threading.Thread(target=_worker, daemon=True, name="topic-echo-watch")
        self._thread.start()
        return self.get_status(project)

    def stop(self, project: Optional[str] = None) -> dict[str, Any]:
        if project and self._project and project != self._project:
            return self.get_status(project)

        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
        self._thread = None
        self._state = "idle"
        self._project = None
        self._topics = []
        return self.get_status(project)


topic_echo_manager = TopicEchoManager()
