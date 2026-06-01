"""TensorBoard subprocess manager, reverse proxy, and scalar parsing."""
from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from domain.models import ScalarSeries, TensorBoardStatus
from storage import project_storage, run_registry

REPO_ROOT = Path(__file__).resolve().parents[3]
TRAIN_VENV_PYTHON = REPO_ROOT / "training" / ".venv" / "bin" / "python"
MONITOR_VENV_PYTHON = REPO_ROOT / "train-monitor" / "backend" / ".venv" / "bin" / "python"


class TensorBoardManager:
    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._project: Optional[str] = None
        self._port: Optional[int] = None
        self._logdir: Optional[str] = None
        self._run_id: Optional[str] = None
        self._last_error: Optional[str] = None

    def _python_executable(self) -> str:
        for candidate in (MONITOR_VENV_PYTHON, TRAIN_VENV_PYTHON):
            if candidate.is_file():
                return str(candidate)
        return sys.executable

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])

    def _local_url(self) -> Optional[str]:
        if self._port is None:
            return None
        return f"http://127.0.0.1:{self._port}"

    def embed_path(self, project: str) -> Optional[str]:
        if not self.is_running() or self._project != project:
            return None
        return f"/api/projects/{project}/tensorboard/view/"

    def status(self, project: Optional[str] = None) -> TensorBoardStatus:
        if project and self._project and project != self._project:
            return TensorBoardStatus(running=False, error=self._last_error)
        if not self.is_running():
            return TensorBoardStatus(running=False, error=self._last_error)
        proj = project or self._project or ""
        embed = self.embed_path(proj)
        return TensorBoardStatus(
            running=True,
            url=self._local_url(),
            embed_url=embed,
            open_url=f"/api/projects/{proj}/tensorboard/view/" if proj else None,
            port=self._port,
            logdir=self._logdir,
            run_id=self._run_id,
        )

    def is_running(self) -> bool:
        if self._process is None:
            return False
        if self._process.poll() is not None:
            self._process = None
            return False
        return True

    def _wait_ready(self, timeout: float = 15.0) -> bool:
        url = self._local_url()
        if not url:
            return False
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.is_running():
                return False
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.25)
        return False

    def start(self, project: str, *, run_id: Optional[str] = None) -> TensorBoardStatus:
        if self.is_running():
            if self._project == project and self._run_id == run_id:
                return self.status(project)
            self.stop()

        logdir = project_storage.runs_dir(project)
        if run_id:
            logdir = logdir / run_id
        logdir.mkdir(parents=True, exist_ok=True)

        if not any(logdir.rglob("events.out.tfevents.*")):
            self._last_error = f"No TensorBoard event files under {logdir}"
            return TensorBoardStatus(running=False, error=self._last_error)

        port = self._free_port()
        cmd = [
            self._python_executable(),
            "-m",
            "tensorboard.main",
            "--logdir",
            str(logdir),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--reload_interval",
            "5",
        ]
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            self._last_error = str(exc)
            return TensorBoardStatus(running=False, error=self._last_error)

        self._project = project
        self._port = port
        self._logdir = str(logdir)
        self._run_id = run_id
        self._last_error = None

        if not self._wait_ready():
            err = ""
            if self._process and self._process.stderr:
                err = (self._process.stderr.read(500) or "").strip()
            if self._process and self._process.poll() is not None:
                self._last_error = err or f"TensorBoard exited with code {self._process.returncode}"
            else:
                self._last_error = err or "TensorBoard did not become ready in time"
            self.stop()
            return TensorBoardStatus(running=False, error=self._last_error)

        return self.status(project)

    def stop(self) -> TensorBoardStatus:
        proc = self._process
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._process = None
        self._project = None
        self._port = None
        self._logdir = None
        self._run_id = None
        return TensorBoardStatus(running=False)

    def local_port(self) -> Optional[int]:
        return self._port if self.is_running() else None

    def serves_project(self, project: str) -> bool:
        return self.is_running() and self._project == project


def read_scalars(project: str, run_id: Optional[str] = None, *, max_points: int = 500) -> list[ScalarSeries]:
    events = run_registry.find_event_files(project, run_id)
    if not events:
        return []

    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    except ImportError:
        return []

    series_map: dict[str, ScalarSeries] = {}
    seen_dirs: set[str] = set()
    for event_path in events:
        logdir = str(event_path.parent)
        if logdir in seen_dirs:
            continue
        seen_dirs.add(logdir)
        try:
            acc = EventAccumulator(logdir, size_guidance={"scalars": max_points})
            acc.Reload()
            for tag in acc.Tags().get("scalars", []):
                events_list = acc.Scalars(tag)
                if not events_list:
                    continue
                steps = [int(e.step) for e in events_list]
                values = [float(e.value) for e in events_list]
                existing = series_map.get(tag)
                if existing is None or len(steps) > len(existing.steps):
                    series_map[tag] = ScalarSeries(tag=tag, steps=steps, values=values)
        except Exception:
            continue
    return sorted(series_map.values(), key=lambda s: s.tag)


tensorboard_manager = TensorBoardManager()
