"""Tests for spawn test manager warmup behavior."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.spawn_test_manager import SpawnTestManager


def test_wait_controller_warmup_completes():
    mgr = SpawnTestManager()
    logs: list[tuple[str, str]] = []
    mgr.subscribe_logs(lambda level, msg: logs.append((level, msg)))
    with patch("api.spawn_test_manager.time.sleep"):
        assert mgr._wait_controller_warmup(10.0) is True
    assert any("Controller warmup 10s" in msg for _, msg in logs)
    assert any("warmup complete" in msg for _, msg in logs)


def test_wait_controller_warmup_zero_is_immediate():
    mgr = SpawnTestManager()
    assert mgr._wait_controller_warmup(0) is True


def test_wait_controller_warmup_honours_stop():
    mgr = SpawnTestManager()
    mgr._stop_event.set()
    assert mgr._wait_controller_warmup(30.0) is False
