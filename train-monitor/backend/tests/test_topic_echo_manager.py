"""Tests for topic echo polling manager."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from api.topic_echo_manager import TopicEchoManager


def test_echo_once_ok():
    mgr = TopicEchoManager()
    setup = MagicMock()
    proc = MagicMock(returncode=0, stdout="---\nheader:\n  stamp:\n    sec: 1\n", stderr="")
    with patch("ev_ros_env.bash_ros_cmd", return_value=proc):
        ok, text = mgr._echo_once("/imu/data", setup, {})
    assert ok is True
    assert "---" in text


def test_start_stop_lifecycle():
    mgr = TopicEchoManager()
    with patch.object(mgr, "_run_loop", side_effect=lambda _p: mgr._stop_event.wait(30)):
        status = mgr.start("demo", topics=["/a"])
        assert status["topics"] == ["/a"]
        assert mgr._project == "demo"
        assert mgr.is_running()
        stopped = mgr.stop("demo")
        assert stopped["state"] == "idle"
