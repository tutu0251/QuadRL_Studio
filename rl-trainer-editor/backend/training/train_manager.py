"""Manage RL training subprocess lifecycle."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Optional

from api.task_manager import task_manager
from exporter.rl_yaml_exporter import export_rl_yaml
from storage import project_storage
from validator.validator import RlTrainerValidator

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TRAIN_SCRIPT = _REPO_ROOT / "training" / "scripts" / "run_rl_train.py"
_TRAINING_VENV_PYTHON = _REPO_ROOT / "training" / ".venv" / "bin" / "python"

_active: dict[str, Any] = {
    "project": None,
    "task_id": None,
    "process": None,
}

_tensorboard_proc: asyncio.subprocess.Process | None = None


def runs_dir(project_name: str) -> Path:
    return project_storage.project_dir(project_name) / "runs"


def _latest_run_dir(project_name: str) -> Path | None:
    root = runs_dir(project_name)
    if not root.is_dir():
        return None
    candidates = sorted(
        (p for p in root.iterdir() if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _tensorboard_port() -> int:
    return int(os.environ.get("TB_PORT", "6006"))


def tensorboard_url(url_host: str, port: int | None = None) -> str:
    port = port if port is not None else _tensorboard_port()
    return f"http://{url_host}:{port}"


def tensorboard_info(
    project_name: str,
    *,
    url_host: str = "localhost",
    port: int | None = None,
) -> dict[str, Any]:
    port = port if port is not None else _tensorboard_port()
    logdir = runs_dir(project_name)
    latest = _latest_run_dir(project_name)
    return {
        "project": project_name,
        "logdir": str(logdir),
        "latest_run": str(latest) if latest else None,
        "command": f"tensorboard --logdir {logdir} --bind_all --port {port}",
        "url": tensorboard_url(url_host, port),
        "bind_host": "0.0.0.0",
        "port": port,
        "running": _tensorboard_proc is not None and _tensorboard_proc.returncode is None,
    }


def _tensorboard_executable() -> str | None:
    venv_tb = _REPO_ROOT / "training" / ".venv" / "bin" / "tensorboard"
    if venv_tb.is_file():
        return str(venv_tb)
    return "tensorboard"


async def _drain_tensorboard_output(proc: asyncio.subprocess.Process) -> None:
    """Read TensorBoard stdout so a full pipe cannot block the subprocess."""
    assert proc.stdout is not None
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
    except Exception:
        pass


async def _read_tensorboard_startup_output(
    proc: asyncio.subprocess.Process, *, timeout: float = 2.0
) -> str:
    assert proc.stdout is not None
    chunks: list[bytes] = []
    try:
        while True:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            if not line:
                break
            chunks.append(line)
            if b"TensorBoard" in line and b"http" in line:
                break
    except asyncio.TimeoutError:
        pass
    return b"".join(chunks).decode("utf-8", errors="replace").strip()


async def start_tensorboard(
    project_name: str,
    port: int | None = None,
    *,
    url_host: str = "localhost",
) -> dict[str, Any]:
    global _tensorboard_proc

    port = port if port is not None else _tensorboard_port()
    info = tensorboard_info(project_name, url_host=url_host, port=port)

    if _tensorboard_proc is not None and _tensorboard_proc.returncode is None:
        return {
            **info,
            "started": False,
            "message": "TensorBoard already running",
            "pid": _tensorboard_proc.pid,
        }

    exe = _tensorboard_executable()
    if exe == "tensorboard" and not Path(exe).is_file():
        import shutil

        if shutil.which("tensorboard") is None:
            raise FileNotFoundError("tensorboard executable not found")

    logdir = runs_dir(project_name)
    logdir.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        exe,
        "--logdir",
        str(logdir),
        "--port",
        str(port),
        "--bind_all",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(_REPO_ROOT),
    )
    startup_log = await _read_tensorboard_startup_output(proc)
    if proc.returncode is not None:
        _tensorboard_proc = None
        detail = startup_log or f"exit code {proc.returncode}"
        raise RuntimeError(f"TensorBoard failed to start: {detail}")

    _tensorboard_proc = proc
    asyncio.create_task(_drain_tensorboard_output(proc))
    result = {
        **info,
        "started": True,
        "pid": proc.pid,
    }
    if startup_log:
        result["startup_log"] = startup_log
    return result


async def stop_tensorboard() -> dict[str, Any]:
    global _tensorboard_proc
    proc = _tensorboard_proc
    if proc is None or proc.returncode is not None:
        _tensorboard_proc = None
        return {"stopped": False, "message": "TensorBoard is not running"}

    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    _tensorboard_proc = None
    return {"stopped": True}


def training_status() -> dict:
    proc = _active.get("process")
    running = proc is not None and proc.returncode is None
    return {
        "running": running,
        "project": _active.get("project"),
        "task_id": _active.get("task_id"),
        "pid": proc.pid if running and proc else None,
    }


def is_training(project: Optional[str] = None) -> bool:
    st = training_status()
    if not st["running"]:
        return False
    if project is None:
        return True
    return st["project"] == project


async def _stream_process_output(proc: asyncio.subprocess.Process, task_id: str) -> int:
    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            level = "error" if "[error]" in text.lower() else "info"
            task_manager.log(task_id, level, text)
    return await proc.wait()


async def stop_training() -> dict:
    proc = _active.get("process")
    project = _active.get("project")
    if proc is None or proc.returncode is not None:
        _active["project"] = None
        _active["task_id"] = None
        _active["process"] = None
        return {"stopped": False, "message": "No training process running"}

    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    tid = _active.get("task_id")
    if tid:
        task_manager.log(tid, "warn", "Training stopped by user")
        task_manager.set_status(tid, "cancelled", {"project": project})

    _active["project"] = None
    _active["task_id"] = None
    _active["process"] = None
    return {"stopped": True, "project": project}


def _python_executable() -> str:
    if _TRAINING_VENV_PYTHON.is_file():
        return str(_TRAINING_VENV_PYTHON)
    return sys.executable


async def start_training(project_name: str, model, *, dry_run: bool = False) -> str:
    if is_training():
        raise RuntimeError(
            f"Training already running for project '{_active.get('project')}'. Stop it first."
        )

    if not _TRAIN_SCRIPT.is_file():
        raise FileNotFoundError(f"Training script not found: {_TRAIN_SCRIPT}")

    result = RlTrainerValidator(model).validate()
    if not result.valid:
        raise ValueError(f"Validation failed: {len(result.errors)} errors")

    project_dir = project_storage.project_dir(project_name)
    export_rl_yaml(model, project_name)

    tid = task_manager.create_task()
    task_manager.set_status(tid, "running")
    task_manager.log(tid, "info", f"Starting training for {project_name}")

    python = _python_executable()
    cmd = [python, str(_TRAIN_SCRIPT), str(project_dir)]
    if dry_run or os.environ.get("QUADRL_TRAIN_DRY_RUN", "").lower() in ("1", "true", "yes"):
        cmd.append("--dry-run")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(_REPO_ROOT),
        env=env,
    )

    _active["project"] = project_name
    _active["task_id"] = tid
    _active["process"] = proc

    task_manager.log(tid, "info", f"Training PID {proc.pid} — logs stream below")

    async def _wait():
        try:
            code = await _stream_process_output(proc, tid)
            if code == 0:
                task_manager.log(tid, "info", "Training completed")
                task_manager.set_status(
                    tid,
                    "completed",
                    {
                        "project": project_name,
                        "checkpoints": str(project_dir / "checkpoints"),
                        "tensorboard_logdir": str(runs_dir(project_name)),
                        "latest_run": str(_latest_run_dir(project_name) or ""),
                        "exit_code": code,
                    },
                )
            else:
                task_manager.log(tid, "error", f"Training exited with code {code}")
                task_manager.set_status(tid, "failed", {"exit_code": code})
        except Exception as e:
            task_manager.log(tid, "error", str(e))
            task_manager.set_status(tid, "failed", {"error": str(e)})
        finally:
            if _active.get("task_id") == tid:
                _active["project"] = None
                _active["task_id"] = None
                _active["process"] = None

    asyncio.create_task(_wait())
    return tid
