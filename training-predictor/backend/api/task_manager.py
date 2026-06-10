"""Thread-safe log store for background tuning studies.

The study runs in a worker thread, so the ppo-planner pattern (cross-thread
``asyncio.Queue``) doesn't apply here. Instead logs are appended under a lock and read by
index, which makes both polling (``GET /logs?since=N``) and SSE streaming trivial and safe.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from uuid import uuid4


class TaskManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._logs: dict[str, list[dict]] = {}

    def create_task(self) -> str:
        tid = str(uuid4())
        with self._lock:
            self._logs[tid] = []
        return tid

    def log(self, task_id: str, level: str, message: str) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        with self._lock:
            if task_id in self._logs:
                self._logs[task_id].append(entry)

    def logs_since(self, task_id: str, since: int = 0) -> tuple[list[dict], int]:
        """Return (new_entries, next_index) for cursor-based reads."""
        with self._lock:
            entries = self._logs.get(task_id)
            if entries is None:
                return [], since
            return entries[since:], len(entries)

    def exists(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._logs

    def bind(self, task_id: str):
        """A ``log(level, message)`` callback bound to one task — what StudySession expects."""
        def _log(level: str, message: str) -> None:
            self.log(task_id, level, message)
        return _log


task_manager = TaskManager()
