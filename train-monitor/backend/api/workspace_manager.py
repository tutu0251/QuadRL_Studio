"""Workspace generate/build/validate — wraps workspace-generator backend."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from domain.models import WorkspaceStatus
from storage import export_scanner, project_storage

REPO_ROOT = Path(__file__).resolve().parents[3]
WS_BACKEND = REPO_ROOT / "workspace-generator" / "backend"
if str(WS_BACKEND) not in sys.path:
    sys.path.insert(0, str(WS_BACKEND))


def _paths(project: str):
    from paths import ProjectPaths

    return ProjectPaths(project, project_storage.PROJECTS_ROOT)


def _readiness_status(paths) -> str | None:
    report_path = paths.readiness_report_path
    if not report_path.is_file():
        return None
    try:
        doc = json.loads(report_path.read_text(encoding="utf-8"))
        return str(doc.get("status", ""))
    except (json.JSONDecodeError, OSError):
        return None


def get_workspace_status(project: str) -> WorkspaceStatus:
    paths = _paths(project)
    exports = export_scanner.scan_exports(project)
    manifest_ok = paths.manifest_path.is_file()
    build_ok = paths.install_setup().is_file()
    readiness = _readiness_status(paths)

    stale = False
    stale_reasons: list[str] = []
    if manifest_ok:
        try:
            from generator.manifest import exports_stale_against_workspace

            stale, stale_reasons = exports_stale_against_workspace(paths)
        except Exception:
            pass

    training_ready = readiness == "ready"
    return WorkspaceStatus(
        project=project,
        state="idle",
        workspace_path=str(paths.workspace_dir),
        manifest_present=manifest_ok,
        build_ready=build_ok,
        exports_stale=stale,
        stale_reasons=stale_reasons,
        readiness_status=readiness,
        training_ready=training_ready,
        sensor_exports_ready=exports.sensor_exports_ready,
        recommended_sim_backend=exports.recommended_sim_backend,
    )


class WorkspaceManager:
    def __init__(self) -> None:
        self._project: Optional[str] = None
        self._operation: Optional[str] = None
        self._state: str = "idle"
        self._task: Optional[asyncio.Task] = None
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
        return self._state in ("running", "starting")

    def get_status(self, project: Optional[str] = None) -> WorkspaceStatus:
        name = project or self._project or ""
        if not name:
            return WorkspaceStatus(project="", state=self._state)
        base = get_workspace_status(name)
        base.state = self._state if self._project == name else "idle"
        base.operation = self._operation
        return base

    async def _run_blocking(self, project: str, operation: str, fn: Callable[[], dict[str, Any]]) -> WorkspaceStatus:
        if self.is_running():
            raise RuntimeError(f"Workspace operation already running ({self._operation})")

        self._project = project
        self._operation = operation
        self._state = "starting"
        self._emit("info", f"[workspace] Starting: {operation}")

        def _log(msg: str) -> None:
            self._emit("info", f"[workspace] {msg}")

        loop = asyncio.get_event_loop()

        def _wrapped() -> dict[str, Any]:
            return fn()

        try:
            self._state = "running"
            result = await loop.run_in_executor(None, _wrapped)
            self._state = "idle"
            self._emit("info", f"[workspace] Finished: {operation}")
            status = get_workspace_status(project)
            status.state = "idle"
            status.operation = operation
            status.last_result = result
            status.finished_at = datetime.now(timezone.utc).isoformat()
            return status
        except Exception as exc:
            self._state = "failed"
            self._emit("error", f"[workspace] {operation} failed: {exc}")
            status = get_workspace_status(project)
            status.state = "failed"
            status.operation = operation
            status.error = str(exc)
            return status
        finally:
            self._operation = None
            if self._state == "running":
                self._state = "idle"

    async def generate(self, project: str) -> WorkspaceStatus:
        def _do() -> dict[str, Any]:
            from generator.workspace_generator import generate_workspace

            self._emit("info", "[workspace] Generating colcon workspace from exports...")
            return generate_workspace(project, project_storage.PROJECTS_ROOT)

        return await self._run_blocking(project, "generate", _do)

    async def build(self, project: str, *, clean: bool = False) -> WorkspaceStatus:
        def _do() -> dict[str, Any]:
            from generator.manifest import exports_stale_against_workspace
            from generator.workspace_generator import generate_workspace
            from validator.build_validator import build_workspace, write_build_report

            paths = _paths(project)
            stale, changed = exports_stale_against_workspace(paths)
            if stale:
                label = ", ".join(changed) if changed else "missing workspace"
                self._emit("info", f"[workspace] Regenerating workspace ({label})...")
                generate_workspace(project, project_storage.PROJECTS_ROOT)
            self._emit("info", "[workspace] colcon build --symlink-install...")
            report = build_workspace(paths, clean_first=clean)
            write_build_report(paths, report)
            if not report.get("success"):
                raise RuntimeError(report.get("message", "colcon build failed"))
            return report

        return await self._run_blocking(project, "build", _do)

    async def validate_exports(self, project: str) -> WorkspaceStatus:
        def _do() -> dict[str, Any]:
            from validator.sensor_export_validator import validate_sensor_exports

            self._emit("info", "[workspace] Validating sensor/control exports...")
            report = validate_sensor_exports(_paths(project))
            if not report.get("valid"):
                raise RuntimeError("; ".join(report.get("errors") or ["invalid exports"]))
            return report

        return await self._run_blocking(project, "validate_exports", _do)

    async def validate(
        self,
        project: str,
        *,
        static_only: bool = False,
        skip_runtime: bool = False,
        skip_build: bool = False,
    ) -> WorkspaceStatus:
        def _do() -> dict[str, Any]:
            from generator.manifest import exports_stale_against_workspace
            from generator.workspace_generator import generate_workspace
            from validator.build_validator import build_workspace, write_build_report
            from validator.runtime_validator import validate_runtime
            from validator.static_validator import validate_static

            paths = _paths(project)
            report: dict[str, Any] = {"project": project, "phases": {}}

            self._emit("info", "[workspace] Phase 1/3: static validation...")
            static = validate_static(paths)
            report["phases"]["static"] = static
            if not static["valid"]:
                report["status"] = "failed"
                paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                raise RuntimeError("; ".join(static.get("errors") or ["static validation failed"]))

            if static_only:
                report["status"] = "static_ok"
                paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                return report

            if not skip_build:
                stale, changed = exports_stale_against_workspace(paths)
                if stale:
                    self._emit("info", "[workspace] Regenerating workspace before build...")
                    generate_workspace(project, project_storage.PROJECTS_ROOT)
                self._emit("info", "[workspace] Phase 2/3: colcon build...")
                build = build_workspace(paths, clean_first=False)
                report["phases"]["build"] = build
                write_build_report(paths, build)
                if not build.get("success"):
                    report["status"] = "failed"
                    paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                    raise RuntimeError(build.get("message", "build failed"))

            if skip_runtime:
                report["status"] = "build_ok"
                paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                return report

            self._emit("info", "[workspace] Phase 3/3: runtime validation (headless Gazebo)...")

            def on_log(msg: str) -> None:
                self._emit("info", f"[workspace] {msg}")

            runtime = validate_runtime(paths, on_log=on_log)
            report["phases"]["runtime"] = runtime
            report["status"] = runtime.get("status", "failed")
            paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            if report["status"] != "ready":
                errors = runtime.get("errors") or []
                raise RuntimeError("; ".join(errors) if errors else f"readiness: {report['status']}")
            return report

        op = "validate_static" if static_only else ("validate_build" if skip_runtime else "validate")
        return await self._run_blocking(project, op, _do)

    async def setup(
        self,
        project: str,
        *,
        static_only: bool = False,
        skip_runtime: bool = False,
    ) -> WorkspaceStatus:
        if self.is_running():
            raise RuntimeError("Workspace operation already running")
        self._emit("info", "[workspace] Full setup: generate → build → validate")
        try:
            await self.generate(project)
            if static_only:
                return await self.validate(project, static_only=True)
            await self.build(project)
            if skip_runtime:
                return await self.validate(project, skip_runtime=True, skip_build=True)
            return await self.validate(project, skip_build=True)
        except Exception:
            return self.get_status(project)


workspace_manager = WorkspaceManager()
