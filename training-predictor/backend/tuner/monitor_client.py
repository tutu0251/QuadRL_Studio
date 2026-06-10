"""Drive the RL Train Monitor's training over its HTTP API.

The predictor does NOT launch training itself — it uses the Train Monitor as the single
training controller (start / stop / resume / status), exactly as the Train Monitor UI does.
The monitor owns the launch contract (cwd, Gazebo warmup, sim-backend resolution, cleanup),
so a trial is just: POST a per-trial config to ``train/start`` and poll ``train/status`` to
completion. Stdlib-only (urllib) so the predictor venv needs no extra dependency.

Train Monitor backend defaults to ``http://127.0.0.1:8006`` (override with
``QUADRL_TRAIN_MONITOR_URL``).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

LogFn = Callable[[str, str], None]

DEFAULT_URL = "http://127.0.0.1:8006"
TERMINAL_STATES = {"idle", "failed"}


class MonitorError(RuntimeError):
    """Train Monitor is unreachable, rejected the request, or the run failed."""


def monitor_base_url(override: Optional[str] = None) -> str:
    return (override or os.environ.get("QUADRL_TRAIN_MONITOR_URL") or DEFAULT_URL).rstrip("/")


class TrainMonitorClient:
    def __init__(self, base_url: Optional[str] = None, *, log: LogFn = lambda l, m: None,
                 timeout: float = 30.0):
        self.base = monitor_base_url(base_url)
        self.log = log
        self.timeout = timeout

    # ---- low-level ----
    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict[str, Any]:
        url = self.base + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise MonitorError(f"{method} {path} -> HTTP {exc.code}: {detail}")
        except urllib.error.URLError as exc:
            raise MonitorError(
                f"cannot reach Train Monitor at {self.base} ({exc.reason}). "
                f"Start its backend (port 8006) or set QUADRL_TRAIN_MONITOR_URL.")

    # ---- endpoints (mirror the Train Monitor UI's calls) ----
    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/health")

    def reachable(self) -> bool:
        try:
            self.health()
            return True
        except MonitorError:
            return False

    def status(self, project: str) -> dict[str, Any]:
        return self._request("GET", f"/api/projects/{project}/train/status")

    def start(self, project: str, *, config_path: Optional[str] = None,
              gazebo_headless: bool = True, dry_run: bool = False,
              resume_checkpoint: Optional[str] = None,
              resume_start_stage: Optional[int] = None) -> dict[str, Any]:
        body: dict[str, Any] = {"dry_run": dry_run, "gazebo_headless": gazebo_headless}
        if config_path:
            body["config_path"] = str(config_path)
        if resume_checkpoint:
            body["resume_checkpoint"] = resume_checkpoint
        if resume_start_stage is not None:
            body["resume_start_stage"] = resume_start_stage
        path = "resume" if resume_checkpoint else "start"
        return self._request("POST", f"/api/projects/{project}/train/{path}", body)

    def stop(self, project: str) -> dict[str, Any]:
        return self._request("POST", f"/api/projects/{project}/train/stop", {})

    # ---- orchestration ----
    def run_to_completion(
        self,
        project: str,
        config_path,
        *,
        gazebo_headless: bool = True,
        dry_run: bool = False,
        resume_checkpoint: Optional[str] = None,
        resume_start_stage: Optional[int] = None,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> dict[str, Any]:
        """Start a run via the monitor and poll until it finishes; return the final status.

        Raises :class:`MonitorError` if the run fails, is stopped, or times out.
        """
        st = self.start(project, config_path=config_path, gazebo_headless=gazebo_headless,
                        dry_run=dry_run, resume_checkpoint=resume_checkpoint,
                        resume_start_stage=resume_start_stage)
        self.log("trial", f"monitor: training started (state={st.get('state')})")
        started = time.time()
        run_id = st.get("run_id")
        last_progress = None

        while True:
            if should_stop():
                self.log("warn", "stop requested → stopping training via monitor")
                try:
                    self.stop(project)
                finally:
                    raise MonitorError("stopped by user")
            if timeout is not None and time.time() - started > timeout:
                self.stop(project)
                raise MonitorError(f"trial exceeded timeout of {timeout}s")
            time.sleep(poll_interval)

            st = self.status(project)
            run_id = st.get("run_id") or run_id
            progress = st.get("progress_message")
            if progress and progress != last_progress:
                stage = st.get("current_stage") or ""
                self.log("train", f"[{stage}] {progress}")
                last_progress = progress

            state = st.get("state")
            if state in TERMINAL_STATES:
                code = st.get("exit_code")
                if state == "failed" or (code not in (None, 0)):
                    raise MonitorError(f"training failed (state={state}, exit_code={code})")
                st["run_id"] = run_id
                return st
