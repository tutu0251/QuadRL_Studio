"""
Geometry Editor API — FastAPI backend (v2).
DEV MODE: No authentication. Bind 0.0.0.0 for LAN access.
"""
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
from domain.measure import (
    measure_angle,
    measure_distance,
    measure_height,
    measure_leg_reach,
    measure_link_length,
)
from domain.models import (
    Frame,
    JointType,
    NamingConvention,
    PrimitiveType,
    Quat,
    RobotModel,
    Vec3,
)
from domain.service import GeometryCore
from exporter.sdf_exporter import SdfConversionError, export_sdf_from_urdf
from exporter.urdf_exporter import export_urdf, urdf_to_string
from storage import project_storage
from templates.registry import list_templates
from validator.validator import GeometryValidator
from validator.runtime_validator import ExportValidationResult, validate_geometry_export

_sessions: dict[str, GeometryCore] = {}
_active_project: Optional[str] = None

DEV_WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  GEOMETRY EDITOR v2 — DEV MODE                               ║
║  No authentication. Do not expose to the public internet.    ║
║  Backend: 0.0.0.0:8000  |  Frontend: 0.0.0.0:5173           ║
╚══════════════════════════════════════════════════════════════╝
"""


def _get_core(project: Optional[str] = None) -> GeometryCore:
    global _active_project
    name = project or _active_project
    if not name:
        raise HTTPException(400, "No active project. Create or load a project first.")
    if name not in _sessions:
        try:
            model = project_storage.load_robot(name)
            _sessions[name] = GeometryCore(model)
        except FileNotFoundError:
            raise HTTPException(404, f"Project not found: {name}")
    return _sessions[name]


def _set_active(name: str, core: GeometryCore) -> None:
    global _active_project
    _active_project = name
    _sessions[name] = core


def _save(name: str, core: GeometryCore) -> None:
    project_storage.save_robot(name, core.get_model())


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(DEV_WARNING)
    project_storage.PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="QuadRL Geometry Editor API", version="2.0.0", lifespan=lifespan)

cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectCreate(BaseModel):
    name: str


class RenameRequest(BaseModel):
    name: str


class LinkCreate(BaseModel):
    name: str
    parent_joint_id: Optional[str] = None


class ChildLinkCreate(BaseModel):
    name: str
    joint_name: str
    joint_type: JointType = JointType.REVOLUTE


class JointCreate(BaseModel):
    name: str
    parent_link_id: str
    child_link_id: str
    joint_type: JointType = JointType.REVOLUTE


class ShapeCreate(BaseModel):
    shape_type: PrimitiveType


class DimensionsUpdate(BaseModel):
    dimensions: list[float]


class TransformUpdate(BaseModel):
    position: Vec3
    rotation: Quat


class ColorUpdate(BaseModel):
    color: str


class JointUpdate(BaseModel):
    originPosition: Optional[Vec3] = None
    originRotation: Optional[Quat] = None
    axis: Optional[Vec3] = None
    lowerLimit: Optional[float] = None
    upperLimit: Optional[float] = None
    defaultValue: Optional[float] = None
    type: Optional[JointType] = None


class MirrorRequest(BaseModel):
    source_prefix: str
    target_prefix: str


class CopyRequest(BaseModel):
    source_prefix: str
    target_prefix: str


class PoseCreate(BaseModel):
    name: str


class MeasureDistanceRequest(BaseModel):
    link_a_id: str
    link_b_id: str


class MeasureHeightRequest(BaseModel):
    link_id: str
    ground_z: float = 0.0


class MeasureLinkLengthRequest(BaseModel):
    child_link_id: str


class MeasureAngleRequest(BaseModel):
    joint_a_id: str
    joint_b_id: str


class MeasureLegReachRequest(BaseModel):
    hip_link_id: str
    foot_link_id: str


class TemplateInsert(BaseModel):
    template_id: str


class NamingConventionUpdate(BaseModel):
    convention: NamingConvention


@app.get("/api/health")
def health():
    return {"status": "ok", "dev_mode": True, "version": "2.0.0", "active_project": _active_project}


@app.get("/api/projects")
def list_projects():
    return {"projects": project_storage.list_projects(), "active": _active_project}


@app.post("/api/projects")
def create_project(body: ProjectCreate):
    core = GeometryCore()
    core.create_project(body.name)
    _save(body.name, core)
    _set_active(body.name, core)
    return {"project": body.name, "model": core.get_model()}


@app.post("/api/projects/{name}/load")
def load_project(name: str):
    model = project_storage.load_robot(name)
    core = GeometryCore(model)
    _set_active(name, core)
    return {"project": name, "model": core.get_model()}


@app.get("/api/projects/{name}/model")
def get_model(name: str):
    return _get_core(name).get_model()


@app.put("/api/projects/{name}/save")
def save_project(name: str):
    core = _get_core(name)
    path = project_storage.save_robot(name, core.get_model())
    return {"saved": str(path)}


@app.put("/api/projects/{name}/naming-convention")
def set_naming_convention(name: str, body: NamingConventionUpdate):
    core = _get_core(name)
    core.set_naming_convention(body.convention)
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/links")
def add_link(name: str, body: LinkCreate):
    core = _get_core(name)
    link = core.add_link(body.name, body.parent_joint_id)
    _save(name, core)
    return link


@app.post("/api/projects/{name}/links/{parent_link_id}/child")
def add_child_link(name: str, parent_link_id: str, body: ChildLinkCreate):
    core = _get_core(name)
    try:
        link, joint = core.add_child_link(parent_link_id, body.name, body.joint_name, body.joint_type)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save(name, core)
    return {"link": link, "joint": joint}


@app.delete("/api/projects/{name}/links/{link_id}")
def remove_link(name: str, link_id: str):
    core = _get_core(name)
    if not core.remove_link(link_id):
        raise HTTPException(404, "Link not found")
    _save(name, core)
    return {"ok": True}


@app.patch("/api/projects/{name}/links/{link_id}")
def rename_link(name: str, link_id: str, body: RenameRequest):
    core = _get_core(name)
    link = core.rename_link(link_id, body.name)
    if not link:
        raise HTTPException(404, "Link not found")
    _save(name, core)
    return link


@app.put("/api/projects/{name}/links/{link_id}/frame")
def update_link_frame(name: str, link_id: str, frame: Frame):
    core = _get_core(name)
    link = core.update_link_frame(link_id, frame)
    if not link:
        raise HTTPException(404, "Link not found")
    _save(name, core)
    return link


@app.post("/api/projects/{name}/joints")
def add_joint(name: str, body: JointCreate):
    core = _get_core(name)
    try:
        joint = core.add_joint(body.name, body.parent_link_id, body.child_link_id, body.joint_type)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save(name, core)
    return joint


@app.delete("/api/projects/{name}/joints/{joint_id}")
def remove_joint(name: str, joint_id: str):
    core = _get_core(name)
    if not core.remove_joint(joint_id):
        raise HTTPException(404, "Joint not found")
    _save(name, core)
    return {"ok": True}


@app.patch("/api/projects/{name}/joints/{joint_id}")
def rename_joint(name: str, joint_id: str, body: RenameRequest):
    core = _get_core(name)
    joint = core.rename_joint(joint_id, body.name)
    if not joint:
        raise HTTPException(404, "Joint not found")
    _save(name, core)
    return joint


@app.put("/api/projects/{name}/joints/{joint_id}")
def update_joint(name: str, joint_id: str, body: JointUpdate):
    core = _get_core(name)
    data = body.model_dump(exclude_none=True)
    joint = core.update_joint(joint_id, **data)
    if not joint:
        raise HTTPException(404, "Joint not found")
    _save(name, core)
    return joint


@app.post("/api/projects/{name}/links/{link_id}/shapes")
def add_shape(name: str, link_id: str, body: ShapeCreate):
    core = _get_core(name)
    shape = core.add_shape(link_id, body.shape_type)
    if not shape:
        raise HTTPException(404, "Link not found")
    _save(name, core)
    return shape


@app.delete("/api/projects/{name}/links/{link_id}/shapes/{shape_id}")
def remove_shape(name: str, link_id: str, shape_id: str):
    core = _get_core(name)
    if not core.remove_shape(link_id, shape_id):
        raise HTTPException(404, "Shape not found")
    _save(name, core)
    return {"ok": True}


@app.put("/api/projects/{name}/links/{link_id}/shapes/{shape_id}/dimensions")
def update_dimensions(name: str, link_id: str, shape_id: str, body: DimensionsUpdate):
    core = _get_core(name)
    shape = core.update_shape_dimensions(link_id, shape_id, body.dimensions)
    if not shape:
        raise HTTPException(404, "Shape not found")
    _save(name, core)
    return shape


@app.put("/api/projects/{name}/links/{link_id}/shapes/{shape_id}/transform")
def update_transform(name: str, link_id: str, shape_id: str, body: TransformUpdate):
    core = _get_core(name)
    shape = core.update_shape_transform(link_id, shape_id, body.position, body.rotation)
    if not shape:
        raise HTTPException(404, "Shape not found")
    _save(name, core)
    return shape


@app.put("/api/projects/{name}/links/{link_id}/shapes/{shape_id}/color")
def update_shape_color(name: str, link_id: str, shape_id: str, body: ColorUpdate):
    core = _get_core(name)
    shape = core.update_shape_color(link_id, shape_id, body.color)
    if not shape:
        raise HTTPException(404, "Shape not found")
    _save(name, core)
    return shape


@app.get("/api/projects/{name}/poses")
def list_poses(name: str):
    return _get_core(name).get_model().poses


@app.post("/api/projects/{name}/poses")
def create_pose(name: str, body: PoseCreate):
    core = _get_core(name)
    pose = core.add_pose(body.name)
    _save(name, core)
    return pose


@app.post("/api/projects/{name}/poses/{pose_id}/save")
def save_pose(name: str, pose_id: str):
    core = _get_core(name)
    pose = core.save_pose(pose_id)
    if not pose:
        raise HTTPException(404, "Pose not found")
    _save(name, core)
    return pose


@app.post("/api/projects/{name}/poses/{pose_id}/load")
def load_pose(name: str, pose_id: str):
    core = _get_core(name)
    pose = core.load_pose(pose_id)
    if not pose:
        raise HTTPException(404, "Pose not found")
    _save(name, core)
    return {"pose": pose, "model": core.get_model()}


@app.post("/api/projects/{name}/mirror")
def mirror_leg(name: str, body: MirrorRequest):
    core = _get_core(name)
    core.mirror_leg(body.source_prefix, body.target_prefix)
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/copy")
def copy_leg(name: str, body: CopyRequest):
    core = _get_core(name)
    core.copy_leg(body.source_prefix, body.target_prefix)
    _save(name, core)
    return core.get_model()


@app.post("/api/projects/{name}/measure/distance")
def measure_distance_api(name: str, body: MeasureDistanceRequest):
    core = _get_core(name)
    r = measure_distance(core.get_model(), body.link_a_id, body.link_b_id)
    if not r:
        raise HTTPException(404, "Link not found")
    return r


@app.post("/api/projects/{name}/measure/height")
def measure_height_api(name: str, body: MeasureHeightRequest):
    core = _get_core(name)
    r = measure_height(core.get_model(), body.link_id, body.ground_z)
    if not r:
        raise HTTPException(404, "Link not found")
    return r


@app.post("/api/projects/{name}/measure/link-length")
def measure_link_length_api(name: str, body: MeasureLinkLengthRequest):
    core = _get_core(name)
    r = measure_link_length(core.get_model(), body.child_link_id)
    if not r:
        raise HTTPException(404, "Link not found")
    return r


@app.post("/api/projects/{name}/measure/angle")
def measure_angle_api(name: str, body: MeasureAngleRequest):
    core = _get_core(name)
    r = measure_angle(core.get_model(), body.joint_a_id, body.joint_b_id)
    if not r:
        raise HTTPException(404, "Joint not found")
    return r


@app.post("/api/projects/{name}/measure/leg-reach")
def measure_leg_reach_api(name: str, body: MeasureLegReachRequest):
    core = _get_core(name)
    r = measure_leg_reach(core.get_model(), body.hip_link_id, body.foot_link_id)
    if not r:
        raise HTTPException(404, "Link not found")
    return r


@app.get("/api/templates")
def get_templates():
    return {"templates": list_templates()}


@app.post("/api/projects/{name}/templates")
def insert_template(name: str, body: TemplateInsert):
    core = _get_core(name)
    try:
        core.apply_template(body.template_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save(name, core)
    return core.get_model()


@app.get("/api/projects/{name}/naming")
def naming_check(name: str):
    core = _get_core(name)
    return {"issues": core.check_naming_conventions()}


def _log_export_validation(tid: str, validation: ExportValidationResult, label: str) -> None:
    status = (validation.details or {}).get("status", "unknown")
    if status == "skipped":
        msg = next(
            (w.message for w in validation.warnings if "skipped" in w.code),
            f"{label} skipped (not installed)",
        )
        task_manager.log(tid, "warning", msg)
        return
    if validation.valid:
        msg = f"{label} passed"
        if validation.warnings:
            msg += f" ({len(validation.warnings)} warning(s))"
        task_manager.log(tid, "info", msg)
        for w in validation.warnings[:5]:
            task_manager.log(tid, "warning", w.message)
        return
    task_manager.log(tid, "warning", f"{label} failed: {len(validation.errors)} error(s)")
    for err in validation.errors[:10]:
        task_manager.log(tid, "error", err.message)
    for w in validation.warnings[:3]:
        task_manager.log(tid, "warning", w.message)


async def _validate_geometry_export(tid: str, exports_dir: Path) -> ExportValidationResult:
    def _runtime_log(message: str) -> None:
        task_manager.log(tid, "info", message.strip())

    task_manager.log(tid, "info", "Running export validation (may take up to 1 minute)…")
    return await asyncio.to_thread(validate_geometry_export, exports_dir, on_log=_runtime_log)


async def _finish_geometry_export(tid: str, payload: dict[str, Any]) -> None:
    exports_dir = project_storage.project_dir(payload["project"]) / "exports"
    validation = await _validate_geometry_export(tid, exports_dir)
    out = {**payload, "exportValidation": validation.model_dump()}
    _log_export_validation(tid, validation, "Export validation")
    status = (validation.details or {}).get("status", "unknown")
    if status == "skipped" or validation.valid:
        task_manager.set_status(tid, "completed", out)
    else:
        task_manager.set_status(tid, "failed", out)


@app.post("/api/projects/{name}/validate")
async def validate_project(name: str):
    core = _get_core(name)
    tid = task_manager.create_task()
    task_manager.set_status(tid, "running")

    async def run():
        task_manager.log(tid, "info", "Starting geometry validation...")
        await asyncio.sleep(0.05)
        validator = GeometryValidator(core.get_model())
        result = validator.validate()
        urdf_xml = urdf_to_string(core.get_model())
        validator.validate_urdf_xml(urdf_xml)
        all_issues = validator.issues
        errors = [i for i in all_issues if i.severity == "error"]
        result = result.model_copy(update={"issues": all_issues, "valid": len(errors) == 0})
        for issue in all_issues:
            task_manager.log(tid, issue.severity, f"[{issue.code}] {issue.message}")
        task_manager.log(tid, "info", f"Validation complete. valid={result.valid}")
        task_manager.set_status(tid, "completed", result.model_dump())

    asyncio.create_task(run())
    return {"task_id": tid}


@app.post("/api/projects/{name}/export/urdf")
async def export_urdf_api(name: str):
    core = _get_core(name)
    validator = GeometryValidator(core.get_model()).validate()
    if not validator.valid:
        raise HTTPException(400, "Model validation failed. Fix errors before export.")
    tid = task_manager.create_task()
    task_manager.set_status(tid, "running")

    async def run():
        task_manager.log(tid, "info", "Exporting URDF...")
        await asyncio.sleep(0.05)
        out = project_storage.export_urdf_path(name)
        export_urdf(core.get_model(), out)
        task_manager.log(tid, "info", f"Exported URDF to {out}")
        await _finish_geometry_export(
            tid,
            {"project": name, "path": str(out), "format": "urdf", "urdf": str(out)},
        )

    asyncio.create_task(run())
    return {"task_id": tid}


@app.post("/api/projects/{name}/export/gazebo")
async def export_gazebo(name: str):
    core = _get_core(name)
    validator = GeometryValidator(core.get_model()).validate()
    if not validator.valid:
        raise HTTPException(400, "Model validation failed. Fix errors before export.")
    tid = task_manager.create_task()
    task_manager.set_status(tid, "running")

    async def run():
        task_manager.log(tid, "info", "Exporting URDF...")
        await asyncio.sleep(0.05)
        urdf_out = project_storage.export_urdf_path(name)
        sdf_out = project_storage.export_sdf_path(name)
        try:
            export_urdf(core.get_model(), urdf_out)
            task_manager.log(tid, "info", f"Exported URDF to {urdf_out}")
            task_manager.log(tid, "info", "Converting URDF to SDF...")
            export_sdf_from_urdf(urdf_out, sdf_out)
        except (SdfConversionError, FileNotFoundError) as e:
            task_manager.log(tid, "error", str(e))
            task_manager.set_status(tid, "failed", {"error": str(e)})
            return
        task_manager.log(tid, "info", f"Exported SDF to {sdf_out}")
        await _finish_geometry_export(
            tid,
            {"project": name, "path": str(sdf_out), "format": "sdf", "urdf": str(urdf_out), "sdf": str(sdf_out)},
        )

    asyncio.create_task(run())
    return {"task_id": tid}


@app.post("/api/projects/{name}/export/both")
async def export_both(name: str):
    core = _get_core(name)
    validator = GeometryValidator(core.get_model()).validate()
    if not validator.valid:
        raise HTTPException(400, "Model validation failed. Fix errors before export.")
    tid = task_manager.create_task()
    task_manager.set_status(tid, "running")

    async def run():
        task_manager.log(tid, "info", "Exporting URDF...")
        await asyncio.sleep(0.05)
        urdf_out = project_storage.export_urdf_path(name)
        sdf_out = project_storage.export_sdf_path(name)
        try:
            export_urdf(core.get_model(), urdf_out)
            task_manager.log(tid, "info", f"Exported URDF: {urdf_out}")
            task_manager.log(tid, "info", "Converting URDF to SDF...")
            export_sdf_from_urdf(urdf_out, sdf_out)
        except (SdfConversionError, FileNotFoundError) as e:
            task_manager.log(tid, "error", str(e))
            task_manager.set_status(tid, "failed", {"error": str(e)})
            return
        task_manager.log(tid, "info", f"Exported SDF: {sdf_out}")
        await _finish_geometry_export(
            tid,
            {"project": name, "urdf": str(urdf_out), "sdf": str(sdf_out)},
        )

    asyncio.create_task(run())
    return {"task_id": tid}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@app.get("/api/projects/{name}/snapshots")
def snapshots_list(name: str):
    return {"snapshots": project_storage.list_snapshots(name)}


@app.post("/api/projects/{name}/snapshots")
def snapshot_create(name: str, label: Optional[str] = None):
    core = _get_core(name)
    snap_id = project_storage.create_snapshot(name, core.get_model(), label)
    return {"snapshot_id": snap_id}


@app.post("/api/projects/{name}/snapshots/{snap_id}/restore")
def snapshot_restore(name: str, snap_id: str):
    model = project_storage.restore_snapshot(name, snap_id)
    core = GeometryCore(model)
    _set_active(name, core)
    project_storage.save_robot(name, model)
    return {"model": model}


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
