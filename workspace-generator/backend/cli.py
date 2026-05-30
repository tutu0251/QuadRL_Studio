"""CLI entry points for workspace generator."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from generator.manifest import exports_stale_against_workspace
from generator.workspace_generator import generate_workspace
from paths import PROJECTS_ROOT, ProjectPaths
from validator.build_validator import build_workspace, write_build_report
from validator.runtime_validator import validate_runtime
from validator.sensor_export_validator import validate_sensor_exports
from validator.static_validator import validate_static


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _paths(name: str, root: Path | None) -> ProjectPaths:
    name = name.strip()
    return ProjectPaths(name, root) if root else ProjectPaths(name)


def cmd_generate(args: argparse.Namespace) -> int:
    args.project = args.project.strip()
    paths = _paths(args.project, args.projects_root)
    if not paths.project_dir.is_dir():
        print(f"Project not found: {paths.project_dir}", file=sys.stderr)
        return 1
    try:
        result = generate_workspace(args.project, paths.projects_root)
    except FileNotFoundError as exc:
        print(f"Generate failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    print(f"Workspace generated at {result['workspace_path']}")
    return 0


def _ensure_workspace_current(paths: ProjectPaths, project: str) -> bool:
    stale, changed = exports_stale_against_workspace(paths)
    if not stale:
        return True
    label = ", ".join(changed) if changed else "missing workspace"
    _log(f"  exports updated ({label}); regenerating workspace...")
    try:
        generate_workspace(project, paths.projects_root)
    except FileNotFoundError as exc:
        print(f"Generate failed: {exc}", file=sys.stderr)
        return False
    return True


def cmd_build(args: argparse.Namespace) -> int:
    args.project = args.project.strip()
    paths = _paths(args.project, args.projects_root)
    if not paths.project_dir.is_dir():
        print(f"Project not found: {paths.project_dir}", file=sys.stderr)
        return 1
    if not _ensure_workspace_current(paths, args.project):
        return 1
    _log(f"Building workspace: {paths.workspace_dir}")
    report = build_workspace(paths, clean_first=args.clean)
    write_build_report(paths, report)
    print(json.dumps(report, indent=2))
    return 0 if report.get("success") else 1


def cmd_validate_exports(args: argparse.Namespace) -> int:
    args.project = args.project.strip()
    paths = _paths(args.project, args.projects_root)
    if not paths.project_dir.is_dir():
        print(f"Project not found: {paths.project_dir}", file=sys.stderr)
        return 1
    report = validate_sensor_exports(paths)
    print(json.dumps(report, indent=2))
    if report.get("warnings"):
        for w in report["warnings"]:
            _log(f"  [warning] {w}")
    if not report.get("valid"):
        for e in report.get("errors") or []:
            _log(f"  [error] {e}")
        return 1
    _log("Sensor exports: OK")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    args.project = args.project.strip()
    paths = _paths(args.project, args.projects_root)
    if not paths.project_dir.is_dir():
        print(f"Project not found: {paths.project_dir}", file=sys.stderr)
        return 1

    report: dict = {"project": args.project, "phases": {}}

    _log("Phase 1/3: static validation...")
    static = validate_static(paths)
    report["phases"]["static"] = static
    if not static["valid"]:
        report["status"] = "failed"
        paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1
    _log("  static: OK")

    if args.static_only:
        report["status"] = "static_ok"
        paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    if not args.skip_build:
        if not _ensure_workspace_current(paths, args.project):
            report["status"] = "failed"
            paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
            return 1
        _log("Phase 2/3: colcon build...")
        build = build_workspace(paths, clean_first=False)
        report["phases"]["build"] = build
        write_build_report(paths, build)
        if not build.get("success"):
            report["status"] = "failed"
            paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
            return 1
        _log("  build: OK")

    if args.skip_runtime:
        report["status"] = "build_ok"
        paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    _log("Phase 3/3: runtime validation (headless Gazebo)...")
    runtime = validate_runtime(paths, on_log=_log)
    report["phases"]["runtime"] = runtime
    if runtime.get("status") == "skipped":
        report["status"] = "skipped"
        paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2
    report["status"] = runtime.get("status", "failed")
    paths.readiness_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] == "ready":
        _log("Training readiness: READY")
        return 0
    _log(f"Training readiness: FAILED ({len(runtime.get('errors', []))} issue(s))")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="QuadRL workspace generator")
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=None,
        help=f"Projects root (default: {PROJECTS_ROOT})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate colcon workspace from exports")
    gen.add_argument("project", help="Project name")
    gen.set_defaults(func=cmd_generate)

    build = sub.add_parser("build", help="Build project workspace")
    build.add_argument("project", help="Project name")
    build.add_argument("--clean", action="store_true", help="Run colcon clean first")
    build.set_defaults(func=cmd_build)

    exports = sub.add_parser("validate-exports", help="Validate sensor-editor RL exports only")
    exports.add_argument("project", help="Project name")
    exports.set_defaults(func=cmd_validate_exports)

    val = sub.add_parser("validate", help="Validate training readiness")
    val.add_argument("project", help="Project name")
    val.add_argument("--static-only", action="store_true")
    val.add_argument("--skip-runtime", action="store_true")
    val.add_argument("--skip-build", action="store_true")
    val.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
