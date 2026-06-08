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

from api.command_builder import build_train_command
from domain.models import TrainStatus
from storage import project_storage, run_registry

REPO_ROOT = Path(__file__).resolve().parents[3]
TRAIN_SCRIPT = REPO_ROOT / "training" / "scripts" / "run_rl_train.py"
GAZEBO_CLEANUP_SCRIPT = REPO_ROOT / "training" / "scripts" / "cleanup_gazebo.py"
TRAIN_VENV_PYTHON = REPO_ROOT / "training" / ".venv" / "bin" / "python"
TRAINING_DIR = REPO_ROOT / "training"
TRAIN_STOP_TIMEOUT_S = float(os.environ.get("QUADRL_TRAIN_STOP_TIMEOUT_S", "30"))

if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

from quadrl_env.display import resolve_display  # noqa: E402


class TrainManager:
    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen[str]] = None
        self._project: Optional[str] = None
        self._run_id: Optional[str] = None
        self._started_at: Optional[str] = None
        self._dry_run = False
        self._gazebo_headless = True
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

    def _cleanup_gazebo_after_train(self) -> None:
        """Stop orphaned Gazebo when training died before env.close() (e.g. SIGKILL / -9)."""
        if not GAZEBO_CLEANUP_SCRIPT.is_file():
            return
        try:
            subprocess.run(
                [self._python_executable(), str(GAZEBO_CLEANUP_SCRIPT)],
                cwd=str(TRAINING_DIR),
                timeout=45,
                capture_output=True,
                text=True,
            )
            self._emit("info", "Gazebo cleanup finished")
        except Exception as exc:
            self._emit("warn", f"Gazebo cleanup failed: {exc}")

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

    def _update_progress(self, line: str) -> bool:
        """Update the live training status from a stdout line.

        Returns True when the line is high-frequency progress/episode telemetry
        (the per-episode and per-rollout ``[train]`` lines). The caller suppresses
        those from the console — their data is surfaced in the status bar instead.
        """
        episode_match = re.search(
            r"\[train\] episode=(?P<episode>\d+) reason=(?P<reason>\S+)"
            r" steps=(?P<steps>\d+) reward=(?P<reward>\S+)",
            line,
        )
        if episode_match:
            self._state.episode_count = int(episode_match.group("episode"))
            reason = episode_match.group("reason")
            if reason and reason != "-":
                self._state.last_termination_reason = reason
                counts = dict(self._state.termination_counts)
                counts[reason] = counts.get(reason, 0) + 1
                self._state.termination_counts = counts
            return True
        stage_match = re.search(r"Stage (\d+/\d+): (.+)", line)
        if stage_match:
            self._state.current_stage = stage_match.group(2).strip()
        progress_match = re.search(r"progress ([\d,]+) / ([\d,]+)", line)
        if progress_match:
            done = progress_match.group(1).replace(",", "")
            total = progress_match.group(2).replace(",", "")
            self._state.progress_message = f"{done} / {total} timesteps"
        summary_match = re.search(
            r"\[train\] stage=(?P<stage>[^ ]+) progress=(?P<done>[\d,]+)/(?P<total>[\d,]+)"
            r" rollout=(?P<rollout>\d+) episodes=(?P<episodes>\d+) last_term=(?P<term>\S+)",
            line,
        )
        if summary_match:
            self._state.current_stage = summary_match.group("stage")
            done = summary_match.group("done").replace(",", "")
            total = summary_match.group("total").replace(",", "")
            self._state.progress_message = f"{done} / {total} timesteps"
            self._state.rollout_count = int(summary_match.group("rollout"))
            self._state.episode_count = int(summary_match.group("episodes"))
            term = summary_match.group("term")
            if term and term != "-":
                self._state.last_termination_reason = term
            return True
        run_match = re.search(r"TensorBoard run root: (.+)", line)
        if run_match:
            run_path = Path(run_match.group(1).strip())
            self._run_id = run_path.name
            self._state.run_id = self._run_id
        return False

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

    @staticmethod
    def _training_env(*, gazebo_headless: bool, controller_apply_delay_s: Optional[float] = None) -> dict[str, str]:
        env = os.environ.copy()
        if controller_apply_delay_s is not None:
            env["QUADRL_SIM_WARMUP_S"] = str(controller_apply_delay_s)
        if gazebo_headless:
            return env
        display = resolve_display()
        if not display:
            raise RuntimeError(
                "No usable X11 display on this host — Gazebo GUI cannot start.\n"
                "Use Headless mode, open a desktop/VNC session (e.g. DISPLAY=:10), "
                "or set QUADRL_DISPLAY before starting Train Monitor."
            )
        env["DISPLAY"] = display
        return env

    async def start(
        self,
        project: str,
        *,
        dry_run: bool = False,
        gazebo_headless: bool = True,
        resume_checkpoint: Optional[str] = None,
        start_stage: Optional[int] = None,
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

        from api.spawn_test_manager import spawn_test_manager

        if spawn_test_manager.is_running():
            self._emit("warn", "[train] Stopping active spawn test before training (avoid duplicate sim.launch)")
            await spawn_test_manager.stop(project)

        from api.spawn_config_manager import controller_apply_delay_for_project

        delay_s = controller_apply_delay_for_project(project)
        train_env = self._training_env(gazebo_headless=gazebo_headless, controller_apply_delay_s=delay_s)

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
        if gazebo_headless:
            cmd.append("--gazebo-headless")
        else:
            cmd.append("--gazebo-gui")
        if resume_checkpoint:
            cmd.extend(["--resume", resume_checkpoint])
        if start_stage is not None:
            cmd.extend(["--start-stage", str(start_stage)])

        shell_cmd = build_train_command(
            project,
            dry_run=dry_run,
            gazebo_headless=gazebo_headless,
            resume_checkpoint=resume_checkpoint,
            start_stage=start_stage,
            config_path=config_path,
            controller_apply_delay_s=delay_s,
        )
        self._state.command = shell_cmd

        self._project = project
        self._dry_run = dry_run
        self._gazebo_headless = gazebo_headless
        self._resume_checkpoint = resume_checkpoint
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._exit_code = None
        self._state = TrainStatus(
            project=project,
            state="starting",
            started_at=self._started_at,
            resume_checkpoint=resume_checkpoint,
            dry_run=dry_run,
            gazebo_headless=gazebo_headless,
        )

        if not gazebo_headless:
            self._emit("info", f"Gazebo GUI using DISPLAY={train_env.get('DISPLAY')}")

        self._emit("info", f"Starting training: {shell_cmd}")

        # Do not use setsid here — killpg(SIGKILL) on stop used to kill the whole session
        # before env.close(), causing exit -9 and orphaned Gazebo GUI processes.
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(REPO_ROOT / "training"),
            env=train_env,
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
                    is_telemetry = self._update_progress(text)
                    # Progress/episode telemetry is surfaced in the status bar, and
                    # per-step spawn chatter is noise — keep the console readable for
                    # everything else.
                    if not is_telemetry and not text.startswith("[train-spawn]"):
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
                                "gazebo_headless": self._gazebo_headless,
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
            self._cleanup_gazebo_after_train()
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
        try:
            # SIGTERM lets run_rl_train stop learn + env.close() + shutdown Gazebo.
            proc.terminate()
        except ProcessLookupError:
            pass

        stop_steps = max(10, int(TRAIN_STOP_TIMEOUT_S * 10))
        for _ in range(stop_steps):
            if proc.poll() is not None:
                break
            await asyncio.sleep(0.1)
        else:
            self._emit("warn", "Training did not exit in time — sending SIGKILL to training only")
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            for _ in range(30):
                if proc.poll() is not None:
                    break
                await asyncio.sleep(0.1)

        self._cleanup_gazebo_after_train()

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
