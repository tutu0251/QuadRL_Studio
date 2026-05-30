"""PPO Planner API — FastAPI backend."""
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
from domain.models import PpoParamsUpdate, PpoPlannerModel, RecommendationResponse, ValidationResult
from domain.planner_core import PlannerCore
from exporter.ppo_yaml_exporter import export_ppo_yaml
from profiler.machine_profiler import profile_machine
from storage import project_storage
from validator.validator import PpoValidator

_sessions: dict[str, PlannerCore] = {}
_active_project: Optional[str] = None

DEV_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  PPO PLANNER — DEV MODE                                      ║
║  No authentication. Backend: 0.0.0.0:8004  Frontend: 5177  ║
╚══════════════════════════════════════════════════════════════╝
"""


def _get_core(project: Optional[str] = None) -> PlannerCore:
    global _active_project
    name = project or _active_project
    if not name:
        raise HTTPException(400, "No active project. Load a project first.")
    if name not in _sessions:
        try:
            model = project_storage.load_ppo(name)
            _sessions[name] = PlannerCore(model)
        except FileNotFoundError:
            raise HTTPException(404, f"No PPO model for '{name}'. Bootstrap or load first.")
    return _sessions[name]


def _set_active(name: str, core: PlannerCore) -> None:
    global _active_project
    _active_project = name
    _sessions[name] = core


def _save(name: str, core: PlannerCore) -> None:
    project_storage.save_ppo(name, core.get_model())


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(DEV_WARNING)
    project_storage.PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="QuadRL PPO Planner API", version="1.0.0", lifespan=lifespan)

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
    return {"status": "ok", "editor": "ppo-planner"}


@app.get("/api/machine")
def get_machine_profile() -> dict:
    return profile_machine().model_dump()


@app.get("/api/projects")
def list_projects():
    projects = project_storage.list_projects()
    return {
        "projects": projects,
        "active": _active_project,
        "details": [
            {
                "name": p,
                "hasSensor": project_storage.has_sensor_pipeline(p),
                "hasPpo": project_storage.has_ppo(p),
            }
            for p in projects
        ],
    }


@app.post("/api/projects/{name}/load")
def load_project(name: str):
    if project_storage.has_ppo(name):
        model = project_storage.load_ppo(name)
        core = PlannerCore(model)
    else:
        core = PlannerCore(PlannerCore.bootstrap_project(name))
        _save(name, core)
    _set_active(name, core)
    return {
        "project": name,
        "model": core.get_model(),
        "hasPpo": True,
    }


@app.post("/api/projects/{name}/bootstrap")
def bootstrap(name: str):
    model = PlannerCore.bootstrap_project(name)
    core = PlannerCore(model)
    _set_active(name, core)
    _save(name, core)
    return {"project": name, "model": core.get_model()}


@app.get("/api/projects/{name}/model")
def get_model(name: str):
    return _get_core(name).get_model()


@app.put("/api/projects/{name}/model")
def put_model(name: str, model: PpoPlannerModel):
    if model.projectName and model.projectName != name:
        raise HTTPException(400, "projectName mismatch")
    model.projectName = name
    core = PlannerCore(model)
    _set_active(name, core)
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/params")
def patch_params(name: str, body: PpoParamsUpdate):
    core = _get_core(name)
    core.patch_params(body)
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/recommend")
def recommend(name: str) -> RecommendationResponse:
    core = _get_core(name)
    resp = core.apply_recommendation()
    _save(name, core)
    return resp


@app.post("/api/projects/{name}/reset-baseline")
def reset_baseline(name: str):
    core = _get_core(name)
    core.reset_to_baseline()
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/validate")
def validate(name: str) -> ValidationResult:
    return PpoValidator(_get_core(name).get_model()).validate()


async def _run_export(name: str, tid: str):
    try:
        core = _get_core(name)
        model = core.get_model()
        result = PpoValidator(model).validate()
        if not result.valid:
            task_manager.log(tid, "error", f"Validation failed: {len(result.errors)} errors")
            task_manager.set_status(tid, "failed", result.model_dump())
            return
        path = export_ppo_yaml(model, name)
        task_manager.log(tid, "info", f"Exported: {path}")
        task_manager.set_status(tid, "completed", {"ppo_config": str(path)})
    except Exception as e:
        task_manager.log(tid, "error", str(e))
        task_manager.set_status(tid, "failed", {"error": str(e)})


@app.post("/api/projects/{name}/export/ppo")
async def export_ppo(name: str):
    core = _get_core(name)
    result = PpoValidator(core.get_model()).validate()
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
