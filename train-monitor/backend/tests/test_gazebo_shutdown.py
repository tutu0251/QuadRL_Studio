"""Tests for graceful Gazebo shutdown helpers."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import gazebo_shutdown as gs


def test_request_ign_server_stop_success():
    with patch.object(gs.subprocess, "run", return_value=MagicMock(returncode=0, stdout="data: true\n", stderr="")):
        assert gs.request_ign_server_stop() is True


def test_request_ign_server_stop_failure():
    with patch.object(gs.subprocess, "run", return_value=MagicMock(returncode=1, stdout="", stderr="no server")):
        assert gs.request_ign_server_stop() is False


def test_graceful_stop_uses_server_control_first():
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 4242
    with patch.object(gs, "request_ign_server_stop", return_value=True) as stop:
        with patch.object(gs, "wait_for_pid_exit", return_value=True):
            gs.graceful_stop_gazebo_process(proc, 4242)
    stop.assert_called()
