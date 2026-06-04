"""Tests for train manager stop race handling."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.train_manager import TrainManager


@pytest.mark.asyncio
async def test_stop_after_process_already_exited():
    mgr = TrainManager()
    proc = MagicMock()
    proc.poll.return_value = 0
    proc.returncode = 0
    proc.pid = 12345
    mgr._process = proc
    mgr._project = "demo"
    mgr._state.state = "running"

    status = await mgr.stop("demo")
    assert status.state == "idle"
    assert mgr._process is None


@pytest.mark.asyncio
async def test_stop_is_noop_when_idle():
    mgr = TrainManager()
    status = await mgr.stop("demo")
    assert status.state == "idle"


@pytest.mark.asyncio
async def test_start_stops_active_spawn_test(monkeypatch):
    from api import train_manager as tm

    mgr = TrainManager()
    stop_calls: list[str] = []

    class FakeSpawnTest:
        def is_running(self) -> bool:
            return True

        async def stop(self, project: str | None = None):
            stop_calls.append(project or "")
            from domain.models import SpawnTestStatus

            return SpawnTestStatus(project=project or "", state="idle")

    if not tm.TRAIN_SCRIPT.is_file():
        pytest.skip("training script not present in this checkout")

    import api.spawn_test_manager as stm

    monkeypatch.setattr(stm, "spawn_test_manager", FakeSpawnTest())
    monkeypatch.setattr(
        "storage.project_storage.has_rl_export",
        lambda _p: True,
    )
    monkeypatch.setattr(
        "api.spawn_config_manager.controller_apply_delay_for_project",
        lambda _p: 0.0,
    )

    proc = MagicMock()
    proc.pid = 99
    proc.poll.return_value = None
    proc.stdout = MagicMock()
    proc.stdout.readline = MagicMock(return_value="")

    monkeypatch.setattr(tm.subprocess, "Popen", MagicMock(return_value=proc))

    await mgr.start("demo", dry_run=True)

    assert stop_calls == ["demo"]
