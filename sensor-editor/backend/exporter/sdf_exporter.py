"""Convert sens RL URDF to Gazebo SDF via gz/ign sdf."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class SdfConversionError(RuntimeError):
    pass


def _sdf_print_command() -> list[str] | None:
    for cmd in ("gz", "ign"):
        if shutil.which(cmd):
            return [cmd, "sdf", "-p"]
    return None


def export_sdf_from_urdf(urdf_path: Path, output_path: Path) -> Path:
    urdf_path = Path(urdf_path).resolve()
    if not urdf_path.is_file():
        raise FileNotFoundError(f"URDF not found: {urdf_path}")
    cmd = _sdf_print_command()
    if cmd is None:
        raise SdfConversionError("SDF export requires gz or ign on PATH.")
    proc = subprocess.run([*cmd, str(urdf_path)], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise SdfConversionError(f"URDF to SDF conversion failed: {detail or 'unknown error'}")
    sdf_text = proc.stdout.strip()
    if not sdf_text.startswith("<"):
        raise SdfConversionError("URDF to SDF conversion produced no SDF XML")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not sdf_text.startswith("<?xml"):
        sdf_text = '<?xml version="1.0" encoding="utf-8"?>\n' + sdf_text
    output_path.write_text(sdf_text + "\n", encoding="utf-8")
    return output_path
