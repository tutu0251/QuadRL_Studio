"""Workspace Gazebo spawn test session — runs until explicitly stopped."""
from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from api.spawn_config_manager import get_spawn_config, resolve_spawn_create_pose
from domain.models import SpawnTestResult, SpawnTestStatus
from storage import project_storage

REPO_ROOT = Path(__file__).resolve().parents[3]
EV_BACKEND = REPO_ROOT / "export-validator" / "backend"
TRAINING_DIR = REPO_ROOT / "training"
if str(EV_BACKEND) not in sys.path:
    sys.path.insert(0, str(EV_BACKEND))
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))


class SpawnTestManager:
    def __init__(self) -> None:
        self._state: str = "idle"
        self._project: Optional[str] = None
        self._headless: bool = True
        self._gz_pid: Optional[int] = None
        self._spawn_valid: bool = False
        self._spawn_errors: list[str] = []
        self._stop_event = threading.Event()
        self._phase_done = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._gz_proc: Optional[subprocess.Popen[Any]] = None
        self._gz_log_path: Optional[Path] = None
        self._log_callbacks: list[Callable[[str, str], None]] = []

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

    def is_running(self) -> bool:
        return self._state in ("starting", "running", "stopping")

    def get_status(self, project: Optional[str] = None) -> SpawnTestStatus:
        if project and self._project and project != self._project:
            return SpawnTestStatus(project=project, state="idle")
        return SpawnTestStatus(
            project=self._project or project or "",
            state=self._state,  # type: ignore[arg-type]
            headless=self._headless,
            spawn_valid=self._spawn_valid if self._state != "idle" else False,
            pid=self._gz_pid,
            errors=list(self._spawn_errors),
        )

    def _launch_env(self, setup: Path, *, headless: bool) -> dict[str, str]:
        from quadrl_env.ros_env import load_ros_environ

        env = load_ros_environ(workspace_setup=setup)
        env["QUADRL_GAZEBO_HEADLESS"] = "1" if headless else "0"
        if headless:
            return env
        from quadrl_env.display import resolve_display

        display = resolve_display()
        if not display:
            raise RuntimeError(
                "No usable X11 display on this host — Gazebo GUI cannot start.\n"
                "Use Headless mode, open a desktop/VNC session (e.g. DISPLAY=:10), "
                "or set QUADRL_DISPLAY before starting Train Monitor."
            )
        env["DISPLAY"] = display
        return env

    def _cleanup_gazebo(self) -> None:
        from quadrl_env.gazebo_cleanup import cleanup_training_gazebo, terminate_process_group

        proc = self._gz_proc
        pid = self._gz_pid
        self._gz_proc = None
        self._gz_pid = None

        if proc is not None and proc.poll() is None:
            terminate_process_group(proc.pid)
        cleanup_training_gazebo(pid)

        if self._gz_log_path and self._gz_log_path.is_file():
            try:
                self._gz_log_path.unlink()
            except OSError:
                pass
            self._gz_log_path = None

    def _wait_controller_warmup(self, delay_s: float) -> bool:
        """Wait after spawn before control would apply. Returns False if stop requested."""
        delay = max(0.0, float(delay_s))
        if delay <= 0:
            return True
        self._emit(
            "info",
            f"[spawn-test] Controller warmup {delay:.0f}s (delay after spawn before control applies)",
        )
        deadline = time.monotonic() + delay
        while time.monotonic() < deadline:
            if self._stop_event.is_set():
                return False
            time.sleep(min(0.5, deadline - time.monotonic()))
        if self._stop_event.is_set():
            return False
        self._emit("info", "[spawn-test] Controller warmup complete")
        return True

    def _sleep_interruptible(self, duration_s: float) -> bool:
        """Sleep up to *duration_s*; return False if stop was requested."""
        deadline = time.monotonic() + max(0.0, duration_s)
        while time.monotonic() < deadline:
            if self._stop_event.is_set():
                return False
            time.sleep(min(0.5, deadline - time.monotonic()))
        return not self._stop_event.is_set()

    def _launch_exited_early(self) -> tuple[bool, str]:
        proc = self._gz_proc
        if proc is None or proc.poll() is None:
            return False, ""
        tail = ""
        if self._gz_log_path and self._gz_log_path.is_file():
            text = self._gz_log_path.read_text(errors="replace")
            tail = text[-800:].strip()
        return True, tail or f"sim.launch exited with code {proc.returncode}"

    def _run_session(self, project: str, *, headless: bool) -> None:
        from api.spawn_pose_apply import apply_workspace_spawn_reset
        from api.spawn_workspace_session import (
            LAUNCH_SPAWN_SETTLE_S,
            build_sim_launch_command,
            require_workspace_setup,
            wait_for_controller_active,
        )
        from quadrl_env.project_config import load_project_artifacts

        self._spawn_valid = False
        self._spawn_errors = []

        try:
            setup = require_workspace_setup(project)
            project_dir = project_storage.project_dir(project)
            load_project_artifacts(project_dir)

            cfg = get_spawn_config(project)
            spawn_pose = resolve_spawn_create_pose(cfg)
            run_env = self._launch_env(setup, headless=headless)

            mode = "headless" if headless else "GUI"
            self._emit("info", f"[spawn-test] Starting {mode} workspace spawn test for {project}")
            self._emit(
                "info",
                "[spawn-test] Target spawn (default + offset): "
                f"x={spawn_pose['x']:.3f} y={spawn_pose['y']:.3f} z={spawn_pose['z']:.3f} "
                f"rpy=({spawn_pose['roll']:.3f}, {spawn_pose['pitch']:.3f}, {spawn_pose['yaw']:.3f})",
            )
            if not headless:
                self._emit("info", f"[spawn-test] DISPLAY={run_env.get('DISPLAY')}")

            self._emit("info", "[spawn-test] Launching ros2 launch sim.launch.py (world flat)...")
            gz_log_handle = tempfile.NamedTemporaryFile(
                mode="w+",
                prefix="tm_spawn_",
                suffix=".log",
                delete=False,
            )
            self._gz_log_path = Path(gz_log_handle.name)
            launch_cmd = build_sim_launch_command(project, headless=headless)
            self._gz_proc = subprocess.Popen(
                ["bash", "-lc", launch_cmd],
                stdout=gz_log_handle,
                stderr=subprocess.STDOUT,
                env=run_env,
                text=True,
                start_new_session=True,
            )
            gz_log_handle.close()
            self._gz_pid = self._gz_proc.pid

            if not self._sleep_interruptible(2.0):
                return
            early, early_msg = self._launch_exited_early()
            if early:
                self._spawn_errors.append(f"sim.launch exited early: {early_msg}")
                self._emit("error", f"[spawn-test] {self._spawn_errors[-1]}")
                return

            self._emit(
                "info",
                f"[spawn-test] Waiting {LAUNCH_SPAWN_SETTLE_S:.0f}s for sim.launch spawn timers...",
            )
            if not self._sleep_interruptible(LAUNCH_SPAWN_SETTLE_S):
                return
            early, early_msg = self._launch_exited_early()
            if early:
                self._spawn_errors.append(f"sim.launch exited: {early_msg}")
                self._emit("error", f"[spawn-test] {self._spawn_errors[-1]}")
                return

            self._emit("info", "[spawn-test] Waiting for robot spawn (joint_state_broadcaster)...")
            ok, err = wait_for_controller_active(
                setup,
                run_env,
                "joint_state_broadcaster",
                timeout_s=90.0,
            )
            if not ok:
                self._spawn_errors.append(err or "Robot spawn not ready")
                self._emit("error", f"[spawn-test] {self._spawn_errors[-1]}")
                return

            if not self._wait_controller_warmup(cfg.controller_apply_delay_s):
                return

            self._emit("info", "[spawn-test] Waiting for joint_trajectory_controller...")
            ok, err = wait_for_controller_active(
                setup,
                run_env,
                "joint_trajectory_controller",
                timeout_s=60.0,
            )
            if not ok:
                self._spawn_errors.append(err or "joint_trajectory_controller not active")
                self._emit("error", f"[spawn-test] {self._spawn_errors[-1]}")
                return

            self._emit("info", "[spawn-test] Applying spawn pose + stand joints via ros2_control...")
            ok, err = apply_workspace_spawn_reset(
                project,
                spawn=spawn_pose,
                env=run_env,
            )
            if not ok:
                self._spawn_errors.append(err or "spawn reset failed")
                self._emit("error", f"[spawn-test] Failed to apply spawn reset: {err}")
                return

            self._spawn_valid = True
            self._emit(
                "info",
                "[spawn-test] Spawn OK — pose + joints applied; session active until Stop test spawn",
            )
            self._state = "running"
            self._stop_event.wait()
        except FileNotFoundError as exc:
            self._spawn_errors.append(str(exc))
            self._emit("error", f"[spawn-test] {exc}")
        except Exception as exc:
            self._spawn_errors.append(str(exc))
            self._emit("error", f"[spawn-test] {exc}")
        finally:
            self._emit("info", "[spawn-test] Shutting down workspace sim...")
            self._cleanup_gazebo()

    async def start(self, project: str, *, headless: bool = True) -> SpawnTestResult:
        if self.is_running():
            raise RuntimeError("Spawn test already running")

        from api.spawn_workspace_session import require_workspace_setup

        require_workspace_setup(project)

        self._project = project
        self._headless = headless
        self._state = "starting"
        self._stop_event.clear()
        self._phase_done.clear()

        def _worker() -> None:
            try:
                self._run_session(project, headless=headless)
            finally:
                self._state = "idle"
                self._project = None
                self._phase_done.set()

        self._thread = threading.Thread(target=_worker, daemon=True, name="spawn-test")
        self._thread.start()

        deadline = time.monotonic() + 180.0
        while time.monotonic() < deadline:
            if self._state == "running":
                break
            if self._phase_done.is_set():
                break
            await asyncio.sleep(0.2)

        if not self._phase_done.is_set() and self._state == "starting":
            self._spawn_errors.append("Timed out waiting for spawn to complete")

        status = "running" if self._state == "running" and self._spawn_valid else (
            "passed" if self._spawn_valid else "failed"
        )
        return SpawnTestResult(
            project=project,
            valid=self._spawn_valid,
            status=status,
            headless=headless,
            state="running" if self._state == "running" else "idle",
            pid=self._gz_pid,
            errors=list(self._spawn_errors),
        )

    async def stop(self, project: Optional[str] = None) -> SpawnTestStatus:
        if project and self._project and project != self._project:
            raise RuntimeError(f"No spawn test running for '{project}'")

        has_process = self._gz_proc is not None or self._gz_pid is not None
        if not self.is_running() and not has_process:
            return self.get_status(project)

        self._state = "stopping"
        self._emit("warn", "[spawn-test] Stop requested — shutting down workspace sim")
        self._stop_event.set()
        self._cleanup_gazebo()

        thread = self._thread
        if thread is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: thread.join(45))

        self._thread = None
        self._state = "idle"
        self._project = None
        self._emit("info", "[spawn-test] Stopped")
        return self.get_status(project)


spawn_test_manager = SpawnTestManager()
