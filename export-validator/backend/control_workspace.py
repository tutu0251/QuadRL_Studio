"""Generate a minimal colcon workspace for control export validation."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from control_paths import ControlProjectPaths

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
WG_BACKEND = Path(__file__).resolve().parents[2] / "workspace-generator" / "backend"
if str(WG_BACKEND) not in sys.path:
    sys.path.insert(0, str(WG_BACKEND))

from generator.urdf_patch import patch_controllers_parameters  # noqa: E402


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def export_robot_sdf(urdf_path: Path, sdf_path: Path) -> None:
    proc = subprocess.run(
        ["ign", "sdf", "-p", str(urdf_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ign sdf failed for {urdf_path}: {proc.stderr or proc.stdout}")
    sdf_path.write_text(proc.stdout, encoding="utf-8")


def control_exports_stale(paths: ControlProjectPaths) -> tuple[bool, list[str]]:
    if not paths.manifest_path.is_file():
        return True, ["workspace not generated"]

    try:
        saved = json.loads(paths.manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, ["invalid control_manifest.json"]

    saved_hashes = {
        str(item.get("path")): item.get("sha256")
        for item in saved.get("files") or []
        if item.get("path")
    }
    changed: list[str] = []
    for path in (paths.ctrl_urdf(), paths.controllers_yaml(), paths.gains_yaml()):
        current = _sha256(path)
        if saved_hashes.get(str(path)) != current:
            changed.append(path.name)
    return len(changed) > 0, changed


def generate_control_workspace(paths: ControlProjectPaths) -> dict:
    missing = [p for p in (paths.ctrl_urdf(), paths.controllers_yaml(), paths.gains_yaml()) if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing control export(s): {', '.join(str(p) for p in missing)}")

    ws = paths.workspace_dir
    desc = paths.description_src()
    bringup = paths.bringup_src()

    if ws.exists():
        shutil.rmtree(ws / "src", ignore_errors=True)
    (ws / "src").mkdir(parents=True, exist_ok=True)
    desc.mkdir(parents=True, exist_ok=True)
    bringup.mkdir(parents=True, exist_ok=True)

    controllers_name = paths.controllers_yaml().name
    controllers_install = (
        ws
        / "install"
        / paths.description_pkg
        / "share"
        / paths.description_pkg
        / "urdf"
        / controllers_name
    ).resolve()

    urdf_text = paths.ctrl_urdf().read_text(encoding="utf-8")
    urdf_text = patch_controllers_parameters(urdf_text, str(controllers_install))

    (desc / "urdf").mkdir(parents=True, exist_ok=True)
    (desc / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.controllers_yaml(), desc / "urdf" / controllers_name)
    shutil.copy2(paths.controllers_yaml(), desc / "config" / controllers_name)
    shutil.copy2(paths.gains_yaml(), desc / "config" / paths.gains_yaml().name)
    (desc / "urdf" / "robot.urdf").write_text(urdf_text, encoding="utf-8")
    export_robot_sdf(desc / "urdf" / "robot.urdf", desc / "urdf" / "robot.sdf")
    sdf_text = (desc / "urdf" / "robot.sdf").read_text(encoding="utf-8")
    (desc / "urdf" / "robot.sdf").write_text(
        patch_controllers_parameters(sdf_text, str(controllers_install)),
        encoding="utf-8",
    )

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), keep_trailing_newline=True)
    ctx = {
        "project_name": paths.project_name,
        "description_pkg": paths.description_pkg,
        "bringup_pkg": paths.bringup_pkg,
    }
    (desc / "package.xml").write_text(env.get_template("description_package.xml.j2").render(**ctx), encoding="utf-8")
    (desc / "CMakeLists.txt").write_text(
        env.get_template("description_CMakeLists.txt.j2").render(**ctx),
        encoding="utf-8",
    )

    (bringup / "launch").mkdir(parents=True, exist_ok=True)
    (bringup / "worlds").mkdir(parents=True, exist_ok=True)
    (bringup / "resource").mkdir(parents=True, exist_ok=True)
    (bringup / "resource" / paths.bringup_pkg).write_text("", encoding="utf-8")
    (bringup / paths.bringup_pkg).mkdir(parents=True, exist_ok=True)
    (bringup / paths.bringup_pkg / "__init__.py").write_text("", encoding="utf-8")

    shutil.copy2(TEMPLATES_DIR / "flat.world", bringup / "worlds" / "flat.world")
    (bringup / "package.xml").write_text(env.get_template("bringup_package.xml.j2").render(**ctx), encoding="utf-8")
    (bringup / "setup.py").write_text(env.get_template("bringup_setup.py.j2").render(**ctx), encoding="utf-8")
    (bringup / "setup.cfg").write_text(env.get_template("bringup_setup.cfg.j2").render(**ctx), encoding="utf-8")
    (bringup / "launch" / "control_readiness.launch.py").write_text(
        env.get_template("control_readiness.launch.py.j2").render(**ctx),
        encoding="utf-8",
    )

    manifest_doc = {
        "version": "1.0",
        "project_name": paths.project_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            {"path": str(paths.ctrl_urdf()), "sha256": _sha256(paths.ctrl_urdf())},
            {"path": str(paths.controllers_yaml()), "sha256": _sha256(paths.controllers_yaml())},
            {"path": str(paths.gains_yaml()), "sha256": _sha256(paths.gains_yaml())},
        ],
    }
    paths.manifest_path.write_text(json.dumps(manifest_doc, indent=2), encoding="utf-8")

    return {
        "generated": True,
        "workspace_path": str(ws),
        "description_pkg": paths.description_pkg,
        "bringup_pkg": paths.bringup_pkg,
        "manifest_path": str(paths.manifest_path),
    }
