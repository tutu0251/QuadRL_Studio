"""Physics Editor API — FastAPI backend."""
from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.task_manager import task_manager
from domain.kinematics import whole_robot_com
from domain.models import (
    CollisionFriction,
    Inertial,
    JointDynamics,
    RobotModel,
    ValidationResult,
)
from domain.physics_core import PhysicsCore
from exporter.sdf_exporter import SdfConversionError, export_sdf_from_urdf
from exporter.urdf_exporter import export_urdf
from storage import project_storage
from validator.validator import PhysicsValidator

_sessions: dict[str, PhysicsCore] = {}
_active_project: Optional[str] = None

DEV_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  PHYSICS EDITOR — DEV MODE                                   ║
║  No authentication. Backend: 0.0.0.0:8001  Frontend: 5174  ║
╚══════════════════════════════════════════════════════════════╝
"""


def _get_core(project: Optional[str] = None) -> PhysicsCore:
    global _active_project
    name = project or _active_project
    if not name:
        raise HTTPException(400, "No active project. Load a project first.")
    if name not in _sessions:
        try:
            model = project_storage.load_physics(name)
            _sessions[name] = PhysicsCore(model)
        except FileNotFoundError:
            raise HTTPException(404, f"No physics model for '{name}'. Import geo URDF first.")
    return _sessions[name]


def _set_active(name: str, core: PhysicsCore) -> None:
    global _active_project
    _active_project = name
    _sessions[name] = core


def _save(name: str, core: PhysicsCore) -> None:
    project_storage.save_physics(name, core.get_model())


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(DEV_WARNING)
    project_storage.PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="QuadRL Physics Editor API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InertialUpdate(BaseModel):
    mass: float
    com: dict[str, float]
    comRotation: dict[str, float]
    ixx: float
    ixy: float = 0.0
    ixz: float = 0.0
    iyy: float
    iyz: float = 0.0
    izz: float


class FrictionUpdate(BaseModel):
    mu: float
    mu2: float
    kp: float = 1e6
    kd: float = 1.0
    enabled: bool = False
    useMu: bool = True
    useMu2: bool = True
    useKp: bool = False
    useKd: bool = False


class DynamicsUpdate(BaseModel):
    damping: float = 0.0
    friction: float = 0.0
    effort: float = 100.0
    velocity: float = 10.0


class EstimateRequest(BaseModel):
    density: float = 1000.0


@app.get("/api/health")
def health():
    return {"status": "ok", "editor": "physics"}


@app.get("/api/projects")
def list_projects():
    projects = project_storage.list_projects()
    return {
        "projects": projects,
        "active": _active_project,
        "details": [
            {
                "name": p,
                "hasGeoUrdf": project_storage.has_geo_urdf(p),
                "hasPhysics": project_storage.has_physics(p),
            }
            for p in projects
        ],
    }


@app.post("/api/projects/{name}/load")
def load_project(name: str):
    if project_storage.has_physics(name):
        model = project_storage.load_physics(name)
        core = PhysicsCore(model)
    else:
        core = PhysicsCore()
    _set_active(name, core)
    return {"project": name, "model": core.get_model(), "hasPhysics": project_storage.has_physics(name)}


@app.post("/api/projects/{name}/import")
def import_geo(name: str):
    """Overwrite physics model from geo_<name>.urdf."""
    core = PhysicsCore()
    try:
        core.import_geo_urdf(name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    _set_active(name, core)
    _save(name, core)
    return {"project": name, "model": core.get_model(), "imported": True}


@app.get("/api/projects/{name}/model")
def get_model(name: str):
    return _get_core(name).get_model()


@app.put("/api/projects/{name}/links/{link_id}/inertial")
def update_inertial(name: str, link_id: str, body: InertialUpdate):
    core = _get_core(name)
    from domain.models import Quat, Vec3

    ins = Inertial(
        mass=body.mass,
        com=Vec3(**body.com),
        comRotation=Quat(**body.comRotation),
        ixx=body.ixx,
        ixy=body.ixy,
        ixz=body.ixz,
        iyy=body.iyy,
        iyz=body.iyz,
        izz=body.izz,
    )
    core.update_inertial(link_id, ins)
    _save(name, core)
    return core.get_model()


@app.put("/api/projects/{name}/links/{link_id}/friction")
def update_friction(name: str, link_id: str, body: FrictionUpdate):
    core = _get_core(name)
    core.update_friction(link_id, CollisionFriction(**body.model_dump()))
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/links/{link_id}/foot")
def set_foot(name: str, link_id: str, is_foot: bool = True):
    core = _get_core(name)
    core.set_is_foot(link_id, is_foot)
    _save(name, core)
    return core.get_model()


@app.put("/api/projects/{name}/joints/{joint_id}/dynamics")
def update_dynamics(name: str, joint_id: str, body: DynamicsUpdate):
    core = _get_core(name)
    core.update_joint_dynamics(joint_id, JointDynamics(**body.model_dump()))
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/links/{link_id}/estimate")
def estimate_link(name: str, link_id: str, body: EstimateRequest = EstimateRequest()):
    core = _get_core(name)
    core.auto_estimate_link(link_id, density=body.density)
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/estimate-all")
def estimate_all(name: str, body: EstimateRequest = EstimateRequest()):
    core = _get_core(name)
    core.auto_estimate_all(density=body.density)
    _save(name, core)
    return core.get_model()


@app.get("/api/projects/{name}/com")
def robot_com(name: str):
    core = _get_core(name)
    com = whole_robot_com(core.get_model())
    return {"com": com.model_dump() if com else None}


@app.post("/api/projects/{name}/validate")
def validate(name: str) -> ValidationResult:
    core = _get_core(name)
    return PhysicsValidator(core.get_model()).validate()


async def _run_export(name: str, tid: str, include_sdf: bool):
    try:
        core = _get_core(name)
        result = PhysicsValidator(core.get_model()).validate()
        if not result.valid:
            task_manager.log(tid, "error", f"Validation failed: {len(result.errors)} errors")
            task_manager.set_status(tid, "failed", result.model_dump())
            return
        urdf_out = project_storage.export_urdf_path(name)
        export_urdf(core.get_model(), urdf_out)
        task_manager.log(tid, "info", f"Wrote {urdf_out}")
        payload: dict[str, Any] = {"urdf": str(urdf_out)}
        if include_sdf:
            sdf_out = project_storage.export_sdf_path(name)
            export_sdf_from_urdf(urdf_out, sdf_out)
            task_manager.log(tid, "info", f"Wrote {sdf_out}")
            payload["sdf"] = str(sdf_out)
        task_manager.set_status(tid, "completed", payload)
    except SdfConversionError as e:
        task_manager.log(tid, "error", str(e))
        task_manager.set_status(tid, "failed", {"error": str(e)})
    except Exception as e:
        task_manager.log(tid, "error", str(e))
        task_manager.set_status(tid, "failed", {"error": str(e)})


@app.post("/api/projects/{name}/export/urdf")
async def export_urdf_route(name: str):
    core = _get_core(name)
    result = PhysicsValidator(core.get_model()).validate()
    if not result.valid:
        raise HTTPException(400, detail=result.model_dump())
    tid = task_manager.create_task()
    asyncio.create_task(_run_export(name, tid, include_sdf=False))
    return {"task_id": tid}


@app.post("/api/projects/{name}/export/gazebo")
async def export_gazebo(name: str):
    core = _get_core(name)
    result = PhysicsValidator(core.get_model()).validate()
    if not result.valid:
        raise HTTPException(400, detail=result.model_dump())
    tid = task_manager.create_task()
    asyncio.create_task(_run_export(name, tid, include_sdf=True))
    return {"task_id": tid}


@app.post("/api/projects/{name}/export/both")
async def export_both(name: str):
    return await export_gazebo(name)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    t = task_manager.get(task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    return t


@app.get("/api/projects/{name}/gazebo-preview")
def gazebo_preview_cmd(name: str):
    sdf = project_storage.export_sdf_path(name)
    return {
        "sdf": str(sdf),
        "command": f"./spawn_gazebo_gui.sh --sdf {sdf} {name}",
        "exists": sdf.is_file(),
    }


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
