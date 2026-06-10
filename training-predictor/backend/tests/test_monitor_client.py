import json

import pytest

from tuner import monitor_client
from tuner.monitor_client import MonitorError, TrainMonitorClient


def test_base_url_default_and_override(monkeypatch):
    monkeypatch.delenv("QUADRL_TRAIN_MONITOR_URL", raising=False)
    assert TrainMonitorClient().base == "http://127.0.0.1:8006"
    monkeypatch.setenv("QUADRL_TRAIN_MONITOR_URL", "http://host:9000/")
    assert TrainMonitorClient().base == "http://host:9000"   # trailing slash trimmed
    assert TrainMonitorClient("http://x:1").base == "http://x:1"  # explicit wins


def _stub_requests(client, responses):
    """Replace _request with a scripted sequence of (method, path) -> dict."""
    calls = []

    def fake(method, path, body=None):
        calls.append((method, path, body))
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    client._request = fake
    return calls


def test_run_to_completion_polls_until_idle():
    client = TrainMonitorClient("http://x")
    logs = []
    client.log = lambda l, m: logs.append((l, m))
    calls = _stub_requests(client, [
        {"state": "running", "run_id": None},                       # start
        {"state": "running", "run_id": "RUN1", "progress_message": "1k/5k"},  # status poll 1
        {"state": "idle", "run_id": "RUN1", "exit_code": 0},          # status poll 2 (terminal)
    ])
    st = client.run_to_completion("proj", "/tmp/cfg.yaml", poll_interval=0)
    assert st["run_id"] == "RUN1"
    assert calls[0][:2] == ("POST", "/api/projects/proj/train/start")
    assert calls[-1][:2] == ("GET", "/api/projects/proj/train/status")


def test_run_to_completion_raises_on_failure():
    client = TrainMonitorClient("http://x")
    _stub_requests(client, [
        {"state": "running"},
        {"state": "failed", "exit_code": 1},
    ])
    with pytest.raises(MonitorError):
        client.run_to_completion("proj", "/tmp/cfg.yaml", poll_interval=0)


def test_run_to_completion_stop_requested():
    client = TrainMonitorClient("http://x")
    _stub_requests(client, [
        {"state": "running"},   # start
        {"ok": True},           # stop call
    ])
    with pytest.raises(MonitorError):
        client.run_to_completion("proj", "/tmp/cfg.yaml", poll_interval=0,
                                 should_stop=lambda: True)


def test_start_uses_resume_path_when_checkpoint_given():
    client = TrainMonitorClient("http://x")
    calls = _stub_requests(client, [{"state": "running"}])
    client.start("proj", config_path="/c.yaml", resume_checkpoint="checkpoints/ppo_walk.zip")
    method, path, body = calls[0]
    assert path == "/api/projects/proj/train/resume"
    assert body["resume_checkpoint"] == "checkpoints/ppo_walk.zip"
    assert body["config_path"] == "/c.yaml"
