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
