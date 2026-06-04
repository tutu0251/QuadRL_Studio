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

from api.command_builder import preview_command
from api.spawn_config_manager import get_spawn_config, update_spawn_config
from api.spawn_test_manager import spawn_test_manager
from api.topic_echo_manager import topic_echo_manager
from api.tensorboard_manager import read_scalars, tensorboard_manager
from api.topics_manager import list_topics, update_confirmations
from api.train_manager import train_manager
from api.training_config_manager import get_training_config, update_training_config
from api.workspace_manager import get_workspace_status, workspace_manager
from domain.models import (
    ProjectSummary,
    SpawnConfigUpdate,
    SpawnTestRequest,
    SpawnTestResult,
    TopicWatchRequest,
    TopicsConfirmUpdate,
    TrainStartRequest,
    TrainStatus,
    TrainingConfigUpdate,
    WorkspaceOperationRequest,
    WorkspaceStatus,
)
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
    if spawn_test_manager.is_running():
        await spawn_test_manager.stop()
    topic_echo_manager.stop()
    if workspace_manager.is_running():
        workspace_manager._state = "idle"
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


@app.get("/api/system/display")
def system_display():
    from display_probe import display_status_dict
    from domain.models import DisplayStatus

    return DisplayStatus(**display_status_dict()).model_dump()


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


@app.get("/api/projects/{name}/commands/preview")
def command_preview(name: str, action: str, params: Optional[str] = None):
    import json

    parsed = {}
    if params:
        try:
            parsed = json.loads(params)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, f"Invalid params JSON: {exc}") from exc
    return preview_command(action, name, parsed)


@app.get("/api/projects/{name}/spawn-config")
def spawn_config_get(name: str):
    return get_spawn_config(name).model_dump()


@app.patch("/api/projects/{name}/spawn-config")
def spawn_config_patch(name: str, body: SpawnConfigUpdate):
    cfg, command = update_spawn_config(name, body)
    return {**cfg.model_dump(), "command": command}


@app.post("/api/projects/{name}/spawn/test")
async def spawn_test(name: str, body: SpawnTestRequest = SpawnTestRequest()):
    from api.command_builder import build_spawn_test_stop_command, build_test_spawn_command
    from api.spawn_config_manager import resolve_spawn_create_pose

    try:
        cfg = get_spawn_config(name)
        result = await spawn_test_manager.start(name, headless=body.headless)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = result.model_dump()
    create_pose = resolve_spawn_create_pose(cfg)
    out["command"] = build_test_spawn_command(name, spawn_pose=create_pose, headless=body.headless)
    out["stop_command"] = build_spawn_test_stop_command(name)
    if result.valid:
        topic_echo_manager.start(name)
    return out


@app.get("/api/projects/{name}/spawn/test/status")
def spawn_test_status(name: str):
    return spawn_test_manager.get_status(name).model_dump()


@app.post("/api/projects/{name}/spawn/test/stop")
async def spawn_test_stop(name: str):
    from api.command_builder import build_spawn_test_stop_command

    try:
        status = await spawn_test_manager.stop(name)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    out["command"] = build_spawn_test_stop_command(name)
    topic_echo_manager.stop(name)
    return out


@app.get("/api/projects/{name}/topics")
def topics_list(name: str):
    return list_topics(name).model_dump()


@app.patch("/api/projects/{name}/topics/confirmations")
def topics_confirm(name: str, body: TopicsConfirmUpdate):
    bundle, command = update_confirmations(name, body.confirmed_topics)
    return {**bundle.model_dump(), "command": command}


@app.get("/api/projects/{name}/topics/watch/status")
def topics_watch_status(name: str):
    return topic_echo_manager.get_status(name)


@app.post("/api/projects/{name}/topics/watch/start")
def topics_watch_start(name: str, body: TopicWatchRequest = TopicWatchRequest()):
    topics = body.topics or None
    try:
        status = topic_echo_manager.start(name, topics=topics)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    from api.command_builder import preview_command

    preview = preview_command("topics_watch_start", name, {"topics": status.get("topics", [])})
    return {**status, "command": preview["command"]}


@app.post("/api/projects/{name}/topics/watch/stop")
def topics_watch_stop(name: str):
    status = topic_echo_manager.stop(name)
    from api.command_builder import preview_command

    preview = preview_command("topics_watch_stop", name)
    return {**status, "command": preview["command"]}


@app.get("/api/projects/{name}/training-config")
def training_config_get(name: str):
    return get_training_config(name).model_dump()


@app.patch("/api/projects/{name}/training-config")
def training_config_patch(name: str, body: TrainingConfigUpdate):
    cfg, command = update_training_config(name, body)
    return {**cfg.model_dump(), "command": command}


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
            gazebo_headless=body.gazebo_headless,
            resume_checkpoint=body.resume_checkpoint,
            config_path=body.config_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    if not out.get("command"):
        from api.spawn_config_manager import controller_apply_delay_for_project

        out["command"] = preview_command(
            "train_start",
            name,
            {
                "dry_run": body.dry_run,
                "gazebo_headless": body.gazebo_headless,
                "controller_apply_delay_s": controller_apply_delay_for_project(name),
            },
        )["command"]
    return out


@app.get("/api/projects/{name}/workspace/status")
def workspace_status(name: str) -> WorkspaceStatus:
    return workspace_manager.get_status(name)


@app.post("/api/projects/{name}/workspace/generate")
async def workspace_generate(name: str):
    try:
        status = await workspace_manager.generate(name)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    out["command"] = preview_command("workspace_generate", name)["command"]
    return out


@app.post("/api/projects/{name}/workspace/build")
async def workspace_build(name: str, body: WorkspaceOperationRequest):
    try:
        status = await workspace_manager.build(name, clean=body.clean)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    action = "workspace_build_clean" if body.clean else "workspace_build"
    out["command"] = preview_command(action, name)["command"]
    return out


@app.post("/api/projects/{name}/workspace/validate-exports")
async def workspace_validate_exports(name: str):
    try:
        status = await workspace_manager.validate_exports(name)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    out["command"] = preview_command("workspace_validate_exports", name)["command"]
    return out


@app.post("/api/projects/{name}/workspace/validate")
async def workspace_validate(name: str, body: WorkspaceOperationRequest):
    try:
        status = await workspace_manager.validate(
            name,
            static_only=body.static_only,
            skip_runtime=body.skip_runtime,
            skip_build=body.skip_build,
        )
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    if body.static_only:
        action = "workspace_validate_static"
    elif body.skip_runtime:
        action = "workspace_validate_no_gazebo"
    else:
        action = "workspace_validate_full"
    out["command"] = preview_command(action, name)["command"]
    return out


@app.post("/api/projects/{name}/workspace/setup")
async def workspace_setup(name: str, body: WorkspaceOperationRequest):
    try:
        status = await workspace_manager.setup(
            name,
            static_only=body.static_only,
            skip_runtime=body.skip_runtime,
        )
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    out["command"] = preview_command("workspace_setup", name)["command"]
    return out


@app.post("/api/projects/{name}/train/stop")
async def train_stop(name: str):
    try:
        status = await train_manager.stop(name)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    out["command"] = preview_command("train_stop", name)["command"]
    return out


@app.post("/api/projects/{name}/train/resume")
async def train_resume(name: str, body: TrainStartRequest):
    if not body.resume_checkpoint:
        raise HTTPException(400, "resume_checkpoint is required")
    try:
        status = await train_manager.start(
            name,
            dry_run=body.dry_run,
            gazebo_headless=body.gazebo_headless,
            resume_checkpoint=body.resume_checkpoint,
            config_path=body.config_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    out = status.model_dump()
    from api.spawn_config_manager import controller_apply_delay_for_project

    out["command"] = preview_command(
        "train_resume",
        name,
        {
            "dry_run": body.dry_run,
            "gazebo_headless": body.gazebo_headless,
            "resume_checkpoint": body.resume_checkpoint,
            "controller_apply_delay_s": controller_apply_delay_for_project(name),
        },
    )["command"]
    return out


@app.get("/api/projects/{name}/tensorboard/status")
def tb_status(name: str):
    return tensorboard_manager.status(name).model_dump()


@app.post("/api/projects/{name}/tensorboard/start")
def tb_start(name: str, run_id: Optional[str] = None):
    out = tensorboard_manager.start(name, run_id=run_id).model_dump()
    out["command"] = preview_command("tensorboard_start", name, {"run_id": run_id})["command"]
    return out


@app.post("/api/projects/{name}/tensorboard/stop")
def tb_stop(name: str):
    out = tensorboard_manager.stop().model_dump()
    out["command"] = preview_command("tensorboard_stop", name)["command"]
    return out


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


def _queue_topic_echo(queue: asyncio.Queue, topic: str, entry: dict) -> None:
    try:
        queue.put_nowait({"type": "topic_echo", "topic": topic, "entry": entry})
    except asyncio.QueueFull:
        pass


@app.websocket("/ws/train/logs")
async def ws_train_logs(ws: WebSocket):
    await ws.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    def on_topic_echo(topic: str, entry: dict) -> None:
        _queue_topic_echo(queue, topic, entry)

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
    workspace_manager.subscribe_logs(on_log)
    spawn_test_manager.subscribe_logs(on_log)
    topic_echo_manager.subscribe(on_topic_echo)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                await ws.send_json(msg)
            except asyncio.TimeoutError:
                status = train_manager.get_status()
                ws_status = workspace_manager.get_status()
                await ws.send_json(
                    {
                        "type": "status",
                        "status": status.model_dump(),
                        "workspace": ws_status.model_dump(),
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        train_manager.unsubscribe_logs(on_log)
        workspace_manager.unsubscribe_logs(on_log)
        spawn_test_manager.unsubscribe_logs(on_log)
        topic_echo_manager.unsubscribe(on_topic_echo)
