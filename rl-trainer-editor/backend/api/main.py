"""RL Trainer Editor API — FastAPI backend."""
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
from domain.models import (
    HyperparamsPatch,
    ParallelPatch,
    RecommendationResponse,
    RlTrainerModel,
    RlTrainerPatch,
    ValidationResult,
)
from domain.trainer_core import TrainerCore
from exporter.rl_yaml_exporter import export_rl_yaml
from planner.curriculum import list_curricula
from profiler.machine_profiler import profile_machine
from storage import project_storage
from validator.validator import RlTrainerValidator

_sessions: dict[str, TrainerCore] = {}
_active_project: Optional[str] = None

DEV_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  RL TRAINER EDITOR — DEV MODE                                ║
║  No authentication. Backend: 0.0.0.0:8005  Frontend: 5178   ║
╚══════════════════════════════════════════════════════════════╝
"""


def _get_core(project: Optional[str] = None) -> TrainerCore:
    global _active_project
    name = project or _active_project
    if not name:
        raise HTTPException(400, "No active project. Load a project first.")
    if name not in _sessions:
        try:
            model = project_storage.load_trainer(name)
            _sessions[name] = TrainerCore(model)
        except FileNotFoundError:
            raise HTTPException(404, f"No RL trainer model for '{name}'. Bootstrap or load first.")
    return _sessions[name]


def _set_active(name: str, core: TrainerCore) -> None:
    global _active_project
    _active_project = name
    _sessions[name] = core


def _save(name: str, core: TrainerCore) -> None:
    project_storage.save_trainer(name, core.get_model())


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(DEV_WARNING)
    project_storage.PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="QuadRL RL Trainer API", version="1.0.0", lifespan=lifespan)

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
    return {"status": "ok", "editor": "rl-trainer-editor"}


@app.get("/api/machine")
def get_machine_profile() -> dict:
    return profile_machine().model_dump()


@app.get("/api/curricula")
def get_curricula():
    return {"curricula": list_curricula()}


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
                "hasTrainer": project_storage.has_trainer(p),
            }
            for p in projects
        ],
    }


@app.post("/api/projects/{name}/load")
def load_project(name: str):
    if project_storage.has_trainer(name):
        model = project_storage.load_trainer(name)
        core = TrainerCore(model)
    else:
        core = TrainerCore(TrainerCore.bootstrap_project(name))
        _save(name, core)
    _set_active(name, core)
    return {
        "project": name,
        "model": core.get_model(),
        "hasTrainer": True,
    }


@app.post("/api/projects/{name}/bootstrap")
def bootstrap(name: str):
    if not project_storage.has_sensor_pipeline(name):
        raise HTTPException(
            400,
            detail="Sensor pipeline required. Export from sensor editor first.",
        )
    model = TrainerCore.bootstrap_project(name)
    core = TrainerCore(model)
    _set_active(name, core)
    _save(name, core)
    return {"project": name, "model": core.get_model()}


@app.get("/api/projects/{name}/model")
def get_model(name: str):
    return _get_core(name).get_model()


@app.put("/api/projects/{name}/model")
def put_model(name: str, model: RlTrainerModel):
    if model.projectName and model.projectName != name:
        raise HTTPException(400, "projectName mismatch")
    model.projectName = name
    core = TrainerCore(model)
    _set_active(name, core)
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/model")
def patch_model(name: str, body: RlTrainerPatch):
    core = _get_core(name)
    core.patch(body)
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/hyperparams")
def patch_hyperparams(name: str, body: HyperparamsPatch):
    core = _get_core(name)
    core.patch_hyperparams(body)
    _save(name, core)
    return core.get_model()


@app.patch("/api/projects/{name}/parallel")
def patch_parallel(name: str, body: ParallelPatch):
    core = _get_core(name)
    core.patch_parallel(body)
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/curriculum/{curriculum_id}")
def apply_curriculum(name: str, curriculum_id: str):
    core = _get_core(name)
    try:
        core.apply_curriculum(curriculum_id)
    except KeyError:
        raise HTTPException(404, f"Unknown curriculum: {curriculum_id}")
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/curriculum/stage/{stage_index}")
def set_curriculum_stage(name: str, stage_index: int):
    core = _get_core(name)
    core.set_curriculum_stage(stage_index)
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
    return RlTrainerValidator(_get_core(name).get_model()).validate()


async def _run_export(name: str, tid: str):
    try:
        core = _get_core(name)
        model = core.get_model()
        result = RlTrainerValidator(model).validate()
        if not result.valid:
            task_manager.log(tid, "error", f"Validation failed: {len(result.errors)} errors")
            task_manager.set_status(tid, "failed", result.model_dump())
            return
        path = export_rl_yaml(model, name)
        task_manager.log(tid, "info", f"Exported: {path}")
        task_manager.set_status(tid, "completed", {"rl_config": str(path)})
    except Exception as e:
        task_manager.log(tid, "error", str(e))
        task_manager.set_status(tid, "failed", {"error": str(e)})


@app.post("/api/projects/{name}/export/rl")
async def export_rl(name: str):
    core = _get_core(name)
    result = RlTrainerValidator(core.get_model()).validate()
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
