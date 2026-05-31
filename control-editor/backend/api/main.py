"""Control Editor API — FastAPI backend."""
from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.task_manager import task_manager
from domain.control_core import ControlCore
from domain.models import ControlModel, TrainingProfile, ValidationResult
from exporter.ros2_control_exporter import export_all
from storage import project_storage
from validator.runtime_validator import validate_control_export
from validator.validator import ControlValidator

_sessions: dict[str, ControlCore] = {}
_active_project: Optional[str] = None

DEV_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  CONTROL EDITOR — DEV MODE                                   ║
║  No authentication. Backend: 0.0.0.0:8002  Frontend: 5175  ║
╚══════════════════════════════════════════════════════════════╝
"""


def _get_core(project: Optional[str] = None) -> ControlCore:
    global _active_project
    name = project or _active_project
    if not name:
        raise HTTPException(400, "No active project. Load a project first.")
    if name not in _sessions:
        try:
            model = project_storage.load_control(name)
            _sessions[name] = ControlCore(model)
        except FileNotFoundError:
            raise HTTPException(404, f"No control model for '{name}'. Import phy URDF first.")
    return _sessions[name]


def _set_active(name: str, core: ControlCore) -> None:
    global _active_project
    _active_project = name
    _sessions[name] = core


def _save(name: str, core: ControlCore) -> None:
    project_storage.save_control(name, core.get_model())


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(DEV_WARNING)
    project_storage.PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="QuadRL Control Editor API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProfileUpdate(BaseModel):
    trainingProfile: TrainingProfile


class JointControlUpdate(BaseModel):
    kp: Optional[float] = None
    kd: Optional[float] = None
    defaultPosition: Optional[float] = None
    actionScale: Optional[float] = None
    effort: Optional[float] = None
    velocity: Optional[float] = None
    lowerLimit: Optional[float] = None
    upperLimit: Optional[float] = None
    enabled: Optional[bool] = None


class SimConfigUpdate(BaseModel):
    simPlugin: Optional[str] = None
    hardwarePlugin: Optional[str] = None
    simPluginFilename: Optional[str] = None
    simPluginClass: Optional[str] = None
    controllerType: Optional[str] = None
    updateRate: Optional[int] = None


@app.get("/api/health")
def health():
    return {"status": "ok", "editor": "control"}


@app.get("/api/projects")
def list_projects():
    projects = project_storage.list_projects()
    return {
        "projects": projects,
        "active": _active_project,
        "details": [
            {
                "name": p,
                "hasPhyUrdf": project_storage.has_phy_urdf(p),
                "hasControl": project_storage.has_control(p),
            }
            for p in projects
        ],
    }


@app.post("/api/projects/{name}/load")
def load_project(name: str):
    if project_storage.has_control(name):
        model = project_storage.load_control(name)
        core = ControlCore(model)
    else:
        core = ControlCore(ControlModel(projectName=name))
    _set_active(name, core)
    return {
        "project": name,
        "model": core.get_model(),
        "hasControl": project_storage.has_control(name),
    }


@app.post("/api/projects/{name}/import")
def import_phy(name: str):
    core = ControlCore()
    try:
        core.import_phy_urdf(name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    _set_active(name, core)
    _save(name, core)
    return {"project": name, "model": core.get_model(), "imported": True}


@app.get("/api/projects/{name}/model")
def get_model(name: str):
    return _get_core(name).get_model()


@app.patch("/api/projects/{name}/profile")
def set_profile(name: str, body: ProfileUpdate):
    core = _get_core(name)
    if body.trainingProfile in (TrainingProfile.PROFILE_B, TrainingProfile.PROFILE_C):
        if not project_storage.has_phy_urdf(name) and not core.get_model().actuatedJoints:
            raise HTTPException(400, "Import phy URDF before selecting placeholder profiles")
    core.set_profile(body.trainingProfile)
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/joints/{joint_name}")
def update_joint(name: str, joint_name: str, body: JointControlUpdate):
    core = _get_core(name)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        core.update_joint(joint_name, updates)
    except KeyError as e:
        raise HTTPException(404, str(e))
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/sim-config")
def update_sim_config(name: str, body: SimConfigUpdate):
    core = _get_core(name)
    m = core.get_model()
    if body.simPlugin is not None:
        m.simPlugin = body.simPlugin
    if body.hardwarePlugin is not None:
        m.hardwarePlugin = body.hardwarePlugin
    if body.simPluginFilename is not None:
        m.simPluginFilename = body.simPluginFilename
    if body.simPluginClass is not None:
        m.simPluginClass = body.simPluginClass
    if body.controllerType is not None:
        m.controllerType = body.controllerType
    if body.updateRate is not None:
        m.updateRate = body.updateRate
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/regenerate")
def regenerate(name: str):
    core = _get_core(name)
    if core.get_model().trainingProfile in (
        TrainingProfile.PROFILE_B,
        TrainingProfile.PROFILE_C,
    ):
        raise HTTPException(
            501,
            detail=f"{core.get_model().trainingProfile.value} is not implemented",
        )
    try:
        core.regenerate()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/validate")
def validate(name: str) -> ValidationResult:
    return ControlValidator(_get_core(name).get_model()).validate()


@app.post("/api/projects/{name}/validate/export")
async def validate_export(name: str):
    tid = task_manager.create_task()
    asyncio.create_task(_run_export_validation(name, tid))
    return {"task_id": tid}


async def _run_export_validation(name: str, tid: str) -> None:
    try:
        urdf_out = project_storage.export_ros2_urdf_path(name)
        if not urdf_out.is_file():
            task_manager.log(tid, "error", f"Missing export URDF: {urdf_out}")
            task_manager.set_status(tid, "failed", {"error": "missing_export_urdf"})
            return

        def _runtime_log(message: str) -> None:
            task_manager.log(tid, "info", message.strip())

        task_manager.log(tid, "info", "Running export validation (may take 2–3 minutes)…")
        export_validation = await asyncio.to_thread(
            validate_control_export,
            name,
            on_log=_runtime_log,
        )
        _log_export_validation(tid, export_validation)
        status = (export_validation.details or {}).get("status", "unknown")
        if status == "skipped" or export_validation.valid:
            task_manager.set_status(
                tid,
                "completed",
                {"exportValidation": export_validation.model_dump()},
            )
        else:
            task_manager.set_status(
                tid,
                "failed",
                {"exportValidation": export_validation.model_dump()},
            )
    except Exception as e:
        task_manager.log(tid, "error", str(e))
        task_manager.set_status(tid, "failed", {"error": str(e)})


@app.post("/api/projects/{name}/validate/gazebo")
async def validate_gazebo(name: str):
    return await validate_export(name)


@app.post("/api/projects/{name}/validate/gazebo/async")
async def validate_gazebo_async(name: str):
    return await validate_export(name)


def _log_export_validation(tid: str, export_validation: ValidationResult) -> None:
    status = (export_validation.details or {}).get("status", "unknown")
    if status == "skipped":
        msg = next(
            (w.message for w in export_validation.warnings if "skipped" in w.code),
            "Export validation skipped (not installed)",
        )
        task_manager.log(tid, "warning", msg)
        return
    if export_validation.valid:
        msg = "Export validation passed"
        if export_validation.warnings:
            msg += f" ({len(export_validation.warnings)} warning(s))"
        task_manager.log(tid, "info", msg)
        for w in export_validation.warnings[:5]:
            task_manager.log(tid, "warning", w.message)
        return
    task_manager.log(
        tid,
        "warning",
        f"Export validation failed: {len(export_validation.errors)} error(s)",
    )
    for err in export_validation.errors[:10]:
        task_manager.log(tid, "error", err.message)
    for w in export_validation.warnings[:3]:
        task_manager.log(tid, "warning", w.message)


async def _run_export(name: str, tid: str):
    try:
        core = _get_core(name)
        model = core.get_model()
        if model.trainingProfile != TrainingProfile.PROFILE_A:
            task_manager.log(tid, "error", f"Export not supported for {model.trainingProfile.value}")
            task_manager.set_status(
                tid,
                "failed",
                {"error": "profile_not_implemented"},
            )
            return

        result = ControlValidator(model).validate()
        if not result.valid:
            task_manager.log(tid, "error", f"Validation failed: {len(result.errors)} errors")
            task_manager.set_status(tid, "failed", result.model_dump())
            return

        phy_path = project_storage.phy_urdf_path(name)
        if not phy_path.is_file():
            task_manager.log(tid, "error", f"Missing {phy_path}")
            task_manager.set_status(tid, "failed", {"error": "no_phy_urdf"})
            return

        urdf_out = project_storage.export_ros2_urdf_path(name)
        ctrl_out = project_storage.export_controllers_yaml_path(name)
        gains_out = project_storage.export_gains_yaml_path(name)
        payload = export_all(model, phy_path, urdf_out, ctrl_out, gains_out)
        for k, v in payload.items():
            task_manager.log(tid, "info", f"Wrote {v}")

        def _runtime_log(message: str) -> None:
            task_manager.log(tid, "info", message.strip())

        task_manager.log(tid, "info", "Running export validation (may take 2–3 minutes)…")
        export_validation = await asyncio.to_thread(
            validate_control_export,
            name,
            on_log=_runtime_log,
        )
        out = {**payload, "exportValidation": export_validation.model_dump()}
        _log_export_validation(tid, export_validation)
        status = (export_validation.details or {}).get("status", "unknown")
        if status == "skipped" or export_validation.valid:
            task_manager.set_status(tid, "completed", out)
        else:
            task_manager.set_status(tid, "failed", out)
    except Exception as e:
        task_manager.log(tid, "error", str(e))
        task_manager.set_status(tid, "failed", {"error": str(e)})


@app.post("/api/projects/{name}/export/ros2_control")
async def export_ros2_control(name: str):
    core = _get_core(name)
    model = core.get_model()
    if model.trainingProfile != TrainingProfile.PROFILE_A:
        raise HTTPException(
            501,
            detail=f"Export not implemented for {model.trainingProfile.value}",
        )
    result = ControlValidator(model).validate()
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
