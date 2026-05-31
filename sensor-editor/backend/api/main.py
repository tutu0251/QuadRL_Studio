"""Sensor Editor API — FastAPI backend."""
from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.task_manager import task_manager
from domain.models import SensorCreate, SensorModel, SensorUpdate, TopicConfigUpdate, ValidationResult
from domain.sensor_core import SensorCore
from exporter.rl_exporter import export_all
from storage import project_storage
from validator.validator import SensorValidator

_sessions: dict[str, SensorCore] = {}
_active_project: Optional[str] = None

DEV_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  SENSOR EDITOR — DEV MODE                                    ║
║  No authentication. Backend: 0.0.0.0:8003  Frontend: 5176  ║
╚══════════════════════════════════════════════════════════════╝
"""


def _get_core(project: Optional[str] = None) -> SensorCore:
    global _active_project
    name = project or _active_project
    if not name:
        raise HTTPException(400, "No active project. Load a project first.")
    if name not in _sessions:
        try:
            model = project_storage.load_sensor(name)
            _sessions[name] = SensorCore(model)
        except FileNotFoundError:
            raise HTTPException(404, f"No sensor model for '{name}'. Import ctrl URDF first.")
    return _sessions[name]


def _set_active(name: str, core: SensorCore) -> None:
    global _active_project
    _active_project = name
    _sessions[name] = core


def _save(name: str, core: SensorCore) -> None:
    project_storage.save_sensor(name, core.get_model())


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(DEV_WARNING)
    project_storage.PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="QuadRL Sensor Editor API", version="1.0.0", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "editor": "sensor"}


@app.get("/api/projects")
def list_projects():
    projects = project_storage.list_projects()
    return {
        "projects": projects,
        "active": _active_project,
        "details": [
            {
                "name": p,
                "hasCtrlUrdf": project_storage.has_ctrl_urdf(p),
                "hasSensor": project_storage.has_sensor(p),
            }
            for p in projects
        ],
    }


@app.post("/api/projects/{name}/load")
def load_project(name: str):
    if project_storage.has_sensor(name):
        model = project_storage.load_sensor(name)
        core = SensorCore(model)
    else:
        core = SensorCore(SensorModel(projectName=name))
    _set_active(name, core)
    return {
        "project": name,
        "model": core.get_model(),
        "hasSensor": project_storage.has_sensor(name),
    }


@app.post("/api/projects/{name}/import/ctrl")
def import_ctrl(name: str):
    core = SensorCore(SensorModel(projectName=name))
    try:
        core.import_ctrl_urdf(name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    _set_active(name, core)
    _save(name, core)
    return {"project": name, "model": core.get_model(), "imported": True}


@app.post("/api/projects/{name}/bootstrap/quadruped")
def bootstrap_quadruped(name: str):
    core = _get_core(name)
    try:
        core.bootstrap_quadruped()
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save(name, core)
    return core.get_model()


@app.get("/api/projects/{name}/model")
def get_model(name: str):
    return _get_core(name).get_model()


@app.put("/api/projects/{name}/model")
def put_model(name: str, model: SensorModel):
    if model.projectName and model.projectName != name:
        raise HTTPException(400, "projectName mismatch")
    model.projectName = name
    core = SensorCore(model)
    _set_active(name, core)
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/topic-config")
def update_topic_config(name: str, body: TopicConfigUpdate):
    core = _get_core(name)
    core.update_topic_config(
        topic_prefix=body.topicPrefix,
        gz_model_name=body.gzModelName,
        update_rate_default=body.updateRateDefault,
    )
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/sensors")
def add_sensor(name: str, body: SensorCreate):
    core = _get_core(name)
    try:
        core.add_sensor(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/sensors/{sensor_id}")
def update_sensor(name: str, sensor_id: str, body: SensorUpdate):
    core = _get_core(name)
    try:
        core.update_sensor(sensor_id, body)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save(name, core)
    return core.get_model()


@app.delete("/api/projects/{name}/sensors/{sensor_id}")
def delete_sensor(name: str, sensor_id: str):
    core = _get_core(name)
    try:
        core.remove_sensor(sensor_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/validate")
def validate(name: str) -> ValidationResult:
    return SensorValidator(_get_core(name).get_model()).validate()


async def _run_export(name: str, tid: str):
    try:
        core = _get_core(name)
        model = core.get_model()
        result = SensorValidator(model).validate()
        if not result.valid:
            task_manager.log(tid, "error", f"Validation failed: {len(result.errors)} errors")
            task_manager.set_status(tid, "failed", result.model_dump())
            return

        payload = export_all(model, name)
        for k, v in payload.items():
            task_manager.log(tid, "info", f"{k}: {v}")

        from validator.runtime_validator import validate_sensor_export

        def _runtime_log(message: str) -> None:
            task_manager.log(tid, "info", message.strip())

        task_manager.log(tid, "info", "Running export validation (may take 2–3 minutes)…")
        runtime_validation = await asyncio.to_thread(
            validate_sensor_export,
            name,
            on_log=_runtime_log,
        )
        out = {**payload, "exportValidation": runtime_validation.model_dump()}
        status = (runtime_validation.details or {}).get("status", "unknown")
        if status == "skipped":
            msg = next(
                (w.message for w in runtime_validation.warnings if "skipped" in w.code),
                "Export validation skipped (not installed)",
            )
            task_manager.log(tid, "warning", msg)
            task_manager.set_status(tid, "completed", out)
            return
        if runtime_validation.valid:
            msg = "Export validation passed"
            if runtime_validation.warnings:
                msg += f" ({len(runtime_validation.warnings)} warning(s))"
            task_manager.log(tid, "info", msg)
            for w in runtime_validation.warnings[:5]:
                task_manager.log(tid, "warning", w.message)
            task_manager.set_status(tid, "completed", out)
            return

        task_manager.log(
            tid,
            "warning",
            f"Export validation failed: {len(runtime_validation.errors)} error(s)",
        )
        for err in runtime_validation.errors[:10]:
            task_manager.log(tid, "error", err.message)
        task_manager.set_status(tid, "failed", out)
    except Exception as e:
        task_manager.log(tid, "error", str(e))
        task_manager.set_status(tid, "failed", {"error": str(e)})


@app.post("/api/projects/{name}/export/rl")
async def export_rl(name: str):
    core = _get_core(name)
    result = SensorValidator(core.get_model()).validate()
    if not result.valid:
        raise HTTPException(400, detail=result.model_dump())
    tid = task_manager.create_task()
    asyncio.create_task(_run_export(name, tid))
    return {"task_id": tid}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    t = task_manager.get(task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    return t


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    q = task_manager.subscribe()
    try:
        while True:
            msg = await q.get()
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        task_manager.unsubscribe(q)
