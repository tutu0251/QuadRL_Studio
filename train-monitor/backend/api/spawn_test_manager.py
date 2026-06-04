"""Headless Gazebo spawn test session — runs until explicitly stopped."""
from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from api.spawn_config_manager import get_spawn_config
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

    def _resolve_model_file(self, project: str) -> Path:
        exports = project_storage.exports_dir(project)
        sdf = exports / f"geo_{project}.sdf"
        urdf = exports / f"geo_{project}.urdf"
        if sdf.is_file():
            return sdf
        if urdf.is_file():
            return urdf
        raise FileNotFoundError(f"Geometry export not found: {sdf} or {urdf}")

    def _spawn_env(self, *, headless: bool) -> dict[str, str]:
        from ev_ros_env import sim_env

        env = sim_env()
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
        from spawn_runtime import _stop_process

        proc = self._gz_proc
        self._gz_proc = None
        self._gz_pid = None
        if proc is not None:
            _stop_process(proc)
        for pattern in ("ign gazebo", "gz sim"):
            subprocess.run(["pkill", "-f", pattern], check=False)
        if self._gz_log_path and self._gz_log_path.is_file():
            try:
                self._gz_log_path.unlink()
            except OSError:
                pass
            self._gz_log_path = None

    def _run_session(self, project: str, *, headless: bool) -> None:
        from spawn_runtime import (
            DEFAULT_WORLD_NAME,
            DEFAULT_WORLD_SDF,
            POST_SPAWN_WAIT_S,
            _analyze_spawn_logs,
            _wait_for_sim,
            check_spawn_stack,
        )
        from ev_ros_env import bash_ros_cmd

        self._spawn_valid = False
        self._spawn_errors = []
        gz_log = ""
        spawn_log = ""
        spawn_rc = 1

        try:
            stack = check_spawn_stack()
            if not stack.get("available"):
                missing = ", ".join(stack.get("missing") or [])
                self._spawn_errors.append(f"Spawn stack unavailable: {missing}")
                return

            model_file = self._resolve_model_file(project)
            cfg = get_spawn_config(project)
            spawn_z = float(cfg.effective_spawn.get("z", 0.5))
            run_env = self._spawn_env(headless=headless)
            create_pkg = stack.get("createPackage")
            if not create_pkg:
                self._spawn_errors.append("ros_gz_sim / ros_ign_gazebo not available")
                return

            mode = "headless" if headless else "GUI"
            self._emit("info", f"[spawn-test] Starting {mode} spawn test for {project}")
            self._emit("info", f"[spawn-test] Model: {model_file.name} spawn_z={spawn_z}")
            if not headless:
                self._emit("info", f"[spawn-test] DISPLAY={run_env.get('DISPLAY')}")

            self._emit("info", "[spawn-test] Launching Gazebo...")
            gz_log_handle = tempfile.NamedTemporaryFile(
                mode="w+",
                prefix="tm_spawn_",
                suffix=".log",
                delete=False,
            )
            self._gz_log_path = Path(gz_log_handle.name)
            gz_args = ["ign", "gazebo"]
            if headless:
                gz_args.append("-s")
            gz_args.append(str(DEFAULT_WORLD_SDF))
            self._gz_proc = subprocess.Popen(
                gz_args,
                stdout=gz_log_handle,
                stderr=subprocess.STDOUT,
                env=run_env,
                text=True,
            )
            gz_log_handle.close()
            self._gz_pid = self._gz_proc.pid

            ready, ready_err = _wait_for_sim(DEFAULT_WORLD_NAME, self._gz_proc, 30.0)
            if not ready:
                self._spawn_errors.append(ready_err or "Gazebo not ready")
                return

            spawn_script = (
                f"ros2 run {create_pkg} create "
                f"-world {DEFAULT_WORLD_NAME} "
                f"-file {model_file.resolve()} "
                f"-name {project} "
                f"-z {spawn_z} "
                f"-allow_renaming true"
            )
            self._emit("info", "[spawn-test] Spawning model...")
            spawn_proc = bash_ros_cmd(spawn_script, timeout=30, env=run_env)
            spawn_log = (spawn_proc.stdout or "") + (spawn_proc.stderr or "")
            spawn_rc = spawn_proc.returncode if spawn_proc.returncode is not None else 1
            time.sleep(POST_SPAWN_WAIT_S)
            if self._gz_log_path.is_file():
                gz_log = self._gz_log_path.read_text(errors="replace")

            errors, _warnings = _analyze_spawn_logs(gz_log, spawn_log, spawn_rc)
            if errors:
                self._spawn_errors = [e.message for e in errors]
                self._emit("error", f"[spawn-test] Spawn failed ({len(errors)} error(s))")
                for msg in self._spawn_errors:
                    self._emit("error", f"[spawn-test] {msg}")
                return

            self._spawn_valid = True
            self._emit("info", "[spawn-test] Spawn OK — session active until Stop test spawn")
            self._state = "running"
            self._stop_event.wait()
        except Exception as exc:
            self._spawn_errors.append(str(exc))
            self._emit("error", f"[spawn-test] {exc}")
        finally:
            self._emit("info", "[spawn-test] Shutting down Gazebo...")
            self._cleanup_gazebo()

    async def start(self, project: str, *, headless: bool = True) -> SpawnTestResult:
        if self.is_running():
            raise RuntimeError("Spawn test already running")

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

        deadline = time.monotonic() + 120.0
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
        if not self.is_running():
            return self.get_status(project)

        self._state = "stopping"
        self._emit("warn", "[spawn-test] Stop requested")
        self._stop_event.set()

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
