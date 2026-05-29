"""Async task status and log broadcasting."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from domain.models import AsyncTaskStatus, TaskLogEntry


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, AsyncTaskStatus] = {}
        self._subscribers: list[asyncio.Queue] = []

    def create_task(self) -> str:
        tid = str(uuid4())
        self._tasks[tid] = AsyncTaskStatus(task_id=tid, status="pending")
        return tid

    def log(self, task_id: str, level: str, message: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        entry = TaskLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
        )
        task.logs.append(entry)
        for q in self._subscribers:
            try:
                q.put_nowait({"type": "log", "task_id": task_id, "entry": entry.model_dump()})
            except asyncio.QueueFull:
                pass

    def set_status(self, task_id: str, status: str, result: Optional[dict[str, Any]] = None) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            if result is not None:
                task.result = result

    def get(self, task_id: str) -> Optional[AsyncTaskStatus]:
        return self._tasks.get(task_id)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)


task_manager = TaskManager()
