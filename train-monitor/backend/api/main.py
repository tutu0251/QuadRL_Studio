"""Train Monitor API — FastAPI backend."""
from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.tensorboard_manager import read_scalars, tensorboard_manager
from api.train_manager import train_manager
from domain.models import ProjectSummary, TrainStartRequest, TrainStatus
from storage import export_scanner, project_storage, run_registry

_active_project: Optional[str] = None

DEV_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  TRAIN MONITOR — DEV MODE                                    ║
║  No authentication. Backend: 0.0.0.0:8006  Frontend: 5179   ║
╚══════════════════════════════════════════════════════════════╝
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(DEV_WARNING)
    project_storage.PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    yield
    if train_manager.is_running():
        await train_manager.stop()
    tensorboard_manager.stop()


app = FastAPI(title="QuadRL Train Monitor API", version="1.0.0", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _project_summary(name: str) -> ProjectSummary:
    exports = export_scanner.scan_exports(name)
    checkpoints = project_storage.list_checkpoints(name)
    runs = run_registry.list_runs(name)
    status = train_manager.get_status(name)
    return ProjectSummary(
        name=name,
        has_rl_export=project_storage.has_rl_export(name),
        has_ppo_export=project_storage.has_ppo_export(name),
        export_count=len(exports.files),
        checkpoint_count=len(checkpoints),
        run_count=len(runs),
        training_state=status.state,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "editor": "train-monitor"}


@app.get("/api/system/stats")
def system_stats():
    from profiler.system_stats import sample_system_stats

    return sample_system_stats()


@app.get("/api/machine/profile")
def machine_profile():
    from profiler.system_stats import machine_profile_dict

    return machine_profile_dict()


@app.get("/api/projects")
def list_projects():
    projects = project_storage.list_projects()
    return {
        "projects": projects,
        "active": _active_project,
        "details": [_project_summary(p).model_dump() for p in projects],
    }


@app.post("/api/projects/{name}/load")
def load_project(name: str):
    global _active_project
    if name not in project_storage.list_projects():
        raise HTTPException(404, f"Project '{name}' not found")
    _active_project = name
    return {"project": name, "summary": _project_summary(name).model_dump()}


@app.get("/api/projects/{name}/exports")
def get_exports(name: str):
    return export_scanner.scan_exports(name).model_dump()


@app.get("/api/projects/{name}/exports/content")
def get_export_content(name: str, path: str):
    try:
        content = export_scanner.read_export_text(name, path)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"path": path, "content": content}


@app.get("/api/projects/{name}/checkpoints")
def get_checkpoints(name: str):
    return {"checkpoints": [c.model_dump() for c in project_storage.list_checkpoints(name)]}


@app.get("/api/projects/{name}/runs")
def get_runs(name: str):
    return {"runs": [r.model_dump() for r in run_registry.list_runs(name)]}


@app.get("/api/projects/{name}/runs/{run_id}")
def get_run(name: str, run_id: str):
    info = run_registry.describe_run(name, run_id)
    if not info:
        raise HTTPException(404, f"Run '{run_id}' not found")
    return info.model_dump()


@app.get("/api/projects/{name}/runs/{run_id}/scalars")
def get_run_scalars(name: str, run_id: str):
    return {"series": [s.model_dump() for s in read_scalars(name, run_id)]}


@app.get("/api/projects/{name}/scalars")
def get_latest_scalars(name: str):
    run_id = run_registry.latest_run_id(name)
    return {
        "run_id": run_id,
        "series": [s.model_dump() for s in read_scalars(name, run_id)],
    }


@app.get("/api/projects/{name}/train/status")
def train_status(name: str) -> TrainStatus:
    return train_manager.get_status(name)


@app.post("/api/projects/{name}/train/start")
async def train_start(name: str, body: TrainStartRequest):
    try:
        status = await train_manager.start(
            name,
            dry_run=body.dry_run,
            resume_checkpoint=body.resume_checkpoint,
            config_path=body.config_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return status.model_dump()


@app.post("/api/projects/{name}/train/stop")
async def train_stop(name: str):
    try:
        status = await train_manager.stop(name)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return status.model_dump()


@app.post("/api/projects/{name}/train/resume")
async def train_resume(name: str, body: TrainStartRequest):
    if not body.resume_checkpoint:
        raise HTTPException(400, "resume_checkpoint is required")
    try:
        status = await train_manager.start(
            name,
            dry_run=body.dry_run,
            resume_checkpoint=body.resume_checkpoint,
            config_path=body.config_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return status.model_dump()


@app.get("/api/projects/{name}/tensorboard/status")
def tb_status(name: str):
    return tensorboard_manager.status(name).model_dump()


@app.post("/api/projects/{name}/tensorboard/start")
def tb_start(name: str, run_id: Optional[str] = None):
    return tensorboard_manager.start(name, run_id=run_id).model_dump()


@app.post("/api/projects/{name}/tensorboard/stop")
def tb_stop(name: str):
    return tensorboard_manager.stop().model_dump()


@app.api_route(
    "/api/projects/{name}/tensorboard/view/{path:path}",
    methods=["GET", "HEAD", "POST"],
)
async def tb_view_proxy(name: str, path: str, request: Request):
    """Reverse-proxy TensorBoard through the API so remote browsers can embed it."""
    import httpx

    port = tensorboard_manager.local_port()
    if port is None or not tensorboard_manager.serves_project(name):
        raise HTTPException(503, "TensorBoard is not running for this project")

    upstream = f"http://127.0.0.1:{port}/{path}"
    if request.url.query:
        upstream = f"{upstream}?{request.url.query}"

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "connection")
    }
    body = await request.body() if request.method in ("POST", "PUT", "PATCH") else None

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            upstream_resp = await client.request(
                request.method,
                upstream,
                headers=headers,
                content=body,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"TensorBoard proxy error: {exc}") from exc

    drop = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    resp_headers = {k: v for k, v in upstream_resp.headers.items() if k.lower() not in drop}
    # Allow iframe embedding from the monitor UI.
    resp_headers.pop("X-Frame-Options", None)
    resp_headers.pop("Content-Security-Policy", None)

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )


@app.websocket("/ws/train/logs")
async def ws_train_logs(ws: WebSocket):
    await ws.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    def on_log(level: str, message: str) -> None:
        try:
            queue.put_nowait(
                {
                    "type": "log",
                    "entry": {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "level": level,
                        "message": message,
                    },
                }
            )
        except asyncio.QueueFull:
            pass

    train_manager.subscribe_logs(on_log)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                await ws.send_json(msg)
            except asyncio.TimeoutError:
                status = train_manager.get_status()
                await ws.send_json({"type": "status", "status": status.model_dump()})
    except WebSocketDisconnect:
        pass
    finally:
        train_manager.unsubscribe_logs(on_log)
