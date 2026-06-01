"""Training subprocess manager — start, stop, resume, log streaming."""
from __future__ import annotations

import asyncio
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from domain.models import TrainStatus
from storage import project_storage, run_registry

REPO_ROOT = Path(__file__).resolve().parents[3]
TRAIN_SCRIPT = REPO_ROOT / "training" / "scripts" / "run_rl_train.py"
TRAIN_VENV_PYTHON = REPO_ROOT / "training" / ".venv" / "bin" / "python"


class TrainManager:
    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen[str]] = None
        self._project: Optional[str] = None
        self._run_id: Optional[str] = None
        self._started_at: Optional[str] = None
        self._dry_run = False
        self._resume_checkpoint: Optional[str] = None
        self._state: TrainStatus = TrainStatus(project="", state="idle")
        self._log_callbacks: list[Callable[[str, str], None]] = []
        self._reader_task: Optional[asyncio.Task] = None
        self._exit_code: Optional[int] = None

    def subscribe_logs(self, callback: Callable[[str, str], None]) -> None:
        self._log_callbacks.append(callback)

    def unsubscribe_logs(self, callback: Callable[[str, str], None]) -> None:
        if callback in self._log_callbacks:
            self._log_callbacks.remove(callback)

    def _emit(self, level: str, message: str) -> None:
        for cb in self._log_callbacks:
            try:
                cb(level, message)
            except Exception:
                pass

    def _python_executable(self) -> str:
        if TRAIN_VENV_PYTHON.is_file():
            return str(TRAIN_VENV_PYTHON)
        return sys.executable

    def _sync_process_state(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is not None:
            if self._state.state in ("running", "starting", "stopping"):
                code = self._process.returncode or 0
                self._state.state = "failed" if code != 0 else "idle"
                self._state.exit_code = code
                self._state.pid = None
            self._process = None

    def _update_progress(self, line: str) -> None:
        stage_match = re.search(r"Stage (\d+/\d+): (.+)", line)
        if stage_match:
            self._state.current_stage = stage_match.group(2).strip()
        progress_match = re.search(r"progress ([\d,]+) / ([\d,]+)", line)
        if progress_match:
            done = progress_match.group(1).replace(",", "")
            total = progress_match.group(2).replace(",", "")
            self._state.progress_message = f"{done} / {total} timesteps"
        run_match = re.search(r"TensorBoard run root: (.+)", line)
        if run_match:
            run_path = Path(run_match.group(1).strip())
            self._run_id = run_path.name
            self._state.run_id = self._run_id

    def get_status(self, project: Optional[str] = None) -> TrainStatus:
        self._sync_process_state()
        if project and self._project and project != self._project:
            return TrainStatus(project=project, state="idle")
        if self._project:
            return self._state.model_copy(update={"project": self._project})
        return TrainStatus(project=project or "", state="idle")

    def is_running(self) -> bool:
        self._sync_process_state()
        return self._process is not None

    async def start(
        self,
        project: str,
        *,
        dry_run: bool = False,
        resume_checkpoint: Optional[str] = None,
        config_path: Optional[str] = None,
    ) -> TrainStatus:
        if self.is_running():
            if self._project == project:
                raise RuntimeError("Training already running for this project")
            raise RuntimeError(f"Training already running for '{self._project}'")

        if not TRAIN_SCRIPT.is_file():
            raise FileNotFoundError(f"Training script not found: {TRAIN_SCRIPT}")

        if not project_storage.has_rl_export(project):
            raise FileNotFoundError(f"Missing RL export for project '{project}'")

        project_dir = project_storage.project_dir(project)
        cmd = [
            self._python_executable(),
            str(TRAIN_SCRIPT),
            str(project_dir),
        ]
        if config_path:
            cmd.extend(["--config", config_path])
        if dry_run:
            cmd.append("--dry-run")
        if resume_checkpoint:
            cmd.extend(["--resume", resume_checkpoint])

        self._project = project
        self._dry_run = dry_run
        self._resume_checkpoint = resume_checkpoint
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._exit_code = None
        self._state = TrainStatus(
            project=project,
            state="starting",
            started_at=self._started_at,
            resume_checkpoint=resume_checkpoint,
            dry_run=dry_run,
        )

        self._emit("info", f"Starting training: {' '.join(cmd)}")

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(REPO_ROOT / "training"),
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )
        self._state.state = "running"
        self._state.pid = self._process.pid

        self._reader_task = asyncio.create_task(self._read_output())
        return self.get_status(project)

    async def _read_output(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        proc = self._process
        try:
            while True:
                line = await asyncio.to_thread(proc.stdout.readline)
                if not line:
                    break
                text = line.rstrip()
                if text:
                    self._update_progress(text)
                    self._emit("info", text)
                    if self._run_id and self._project:
                        run_registry.write_monitor_state(
                            self._project,
                            self._run_id,
                            {
                                "pid": self._state.pid,
                                "status": "running",
                                "started_at": self._started_at,
                                "current_stage": self._state.current_stage,
                                "progress_message": self._state.progress_message,
                                "resume_checkpoint": self._resume_checkpoint,
                                "dry_run": self._dry_run,
                            },
                        )
        finally:
            code = proc.wait()
            self._exit_code = code
            status = "completed" if code == 0 else "failed"
            self._state.state = "failed" if code != 0 else "idle"
            self._state.exit_code = code
            self._state.pid = None
            if self._run_id and self._project:
                run_registry.write_monitor_state(
                    self._project,
                    self._run_id,
                    {
                        "status": status,
                        "ended_at": datetime.now(timezone.utc).isoformat(),
                        "exit_code": code,
                        "current_stage": self._state.current_stage,
                        "progress_message": self._state.progress_message,
                    },
                )
            self._emit("info" if code == 0 else "error", f"Training process exited with code {code}")
            self._process = None

    async def stop(self, project: Optional[str] = None) -> TrainStatus:
        self._sync_process_state()
        proc = self._process
        if proc is None:
            return self.get_status(project)

        if project and self._project and project != self._project:
            raise RuntimeError(f"No training running for '{project}'")

        self._state.state = "stopping"
        self._emit("warn", "Stopping training (SIGTERM)…")
        pid = proc.pid
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            else:
                proc.terminate()
        except ProcessLookupError:
            pass

        for _ in range(50):
            if proc.poll() is not None:
                break
            await asyncio.sleep(0.1)
        else:
            self._emit("warn", "Force killing training process")
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                else:
                    proc.kill()
            except ProcessLookupError:
                pass

        if self._run_id and self._project:
            run_registry.write_monitor_state(
                self._project,
                self._run_id,
                {
                    "status": "stopped",
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "exit_code": proc.returncode if proc.poll() is not None else self._exit_code,
                },
            )
        self._process = None
        self._state.state = "idle"
        self._state.pid = None
        return self.get_status(project)


train_manager = TrainManager()
