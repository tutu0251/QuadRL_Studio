"""Load RL / sensor / control exports for a QuadRL project."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

_SPAWN_KEYS = ("x", "y", "z", "roll", "pitch", "yaw")
_SAMPLE_EPS = 1e-9
_DEFAULT_SAMPLE_RANGE: dict[str, float] = {
    "x": 0.02,
    "y": 0.02,
    "z": 0.01,
    "roll": 0.02,
    "pitch": 0.02,
    "yaw": 0.02,
}


@dataclass
class SpawnOffset:
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
    droll: float = 0.0
    dpitch: float = 0.0
    dyaw: float = 0.0


def _spawn_dict(raw: dict[str, Any] | None) -> dict[str, float]:
    base = raw or {}
    return {k: float(base.get(k, 0.0)) for k in _SPAWN_KEYS}


def _offset_from_doc(doc: dict[str, Any]) -> SpawnOffset:
    raw = doc.get("spawn_offset") or {}
    return SpawnOffset(
        dx=float(raw.get("dx", 0.0)),
        dy=float(raw.get("dy", 0.0)),
        dz=float(raw.get("dz", 0.0)),
        droll=float(raw.get("droll", 0.0)),
        dpitch=float(raw.get("dpitch", 0.0)),
        dyaw=float(raw.get("dyaw", 0.0)),
    )


def _base_spawn_from_doc(doc: dict[str, Any], offset: SpawnOffset) -> dict[str, float]:
    stored = doc.get("_base_spawn")
    if isinstance(stored, dict):
        return _spawn_dict(stored)
    effective = _spawn_dict(doc.get("spawn"))
    return {
        "x": effective["x"] - offset.dx,
        "y": effective["y"] - offset.dy,
        "z": effective["z"] - offset.dz,
        "roll": effective["roll"] - offset.droll,
        "pitch": effective["pitch"] - offset.dpitch,
        "yaw": effective["yaw"] - offset.dyaw,
    }


def _effective_spawn(base: dict[str, float], offset: SpawnOffset) -> dict[str, float]:
    return {
        "x": base["x"] + offset.dx,
        "y": base["y"] + offset.dy,
        "z": base["z"] + offset.dz,
        "roll": base["roll"] + offset.droll,
        "pitch": base["pitch"] + offset.dpitch,
        "yaw": base["yaw"] + offset.dyaw,
    }


def sample_spawn_pose(
    base_spawn: dict[str, float],
    offset: SpawnOffset,
    *,
    rng: np.random.Generator | None = None,
) -> dict[str, float]:
    """Uniform sample per axis in [-|offset|, +|offset|]; epsilon fallback when offset ~0."""
    gen = rng if rng is not None else np.random.default_rng()
    axis_offset = {
        "x": offset.dx,
        "y": offset.dy,
        "z": offset.dz,
        "roll": offset.droll,
        "pitch": offset.dpitch,
        "yaw": offset.dyaw,
    }
    out: dict[str, float] = {}
    for axis in _SPAWN_KEYS:
        mag = abs(float(axis_offset[axis]))
        if mag < _SAMPLE_EPS:
            mag = _DEFAULT_SAMPLE_RANGE[axis]
        delta = float(gen.uniform(-mag, mag))
        out[axis] = float(base_spawn[axis]) + delta
    return out


def load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    if path.suffix.lower() == ".json":
        return json.loads(body) or {}
    return yaml.safe_load(body) or {}


def merge_ppo_into_rl(config: dict, project_dir: Path) -> dict:
    ppo_file = config.get("ppo_config_file")
    if not ppo_file:
        return config
    ppo_path = Path(ppo_file)
    if not ppo_path.is_absolute():
        ppo_path = project_dir / "exports" / ppo_file
    if not ppo_path.is_file():
        return config
    ppo = load_yaml(ppo_path)
    merged = dict(config)
    for key in ("hyperparameters", "parallel", "device", "checkpoint", "best_model"):
        if key in ppo:
            merged[key] = ppo[key]
    return merged


@dataclass
class JointGains:
    name: str
    kp: float = 30.0
    kd: float = 0.9
    default_position: float = 0.0
    action_scale: float = 0.25
    effort_limit: float = 80.0
    velocity_limit: float = 10.0


@dataclass
class ProjectArtifacts:
    project_dir: Path
    project_name: str
    rl_config: dict[str, Any]
    observations_doc: dict[str, Any]
    controllers_doc: dict[str, Any]
    gains_doc: dict[str, Any]
    joint_names: list[str]
    joint_gains: dict[str, JointGains]
    control_dt: float = 0.02
    workspace_setup: Path | None = None
    bringup_pkg: str | None = None
    base_spawn: dict[str, float] = field(
        default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0}
    )
    spawn_offset: SpawnOffset = field(default_factory=SpawnOffset)
    spawn_config: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0})

    def sample_spawn(self, *, rng: np.random.Generator | None = None) -> dict[str, float]:
        return sample_spawn_pose(self.base_spawn, self.spawn_offset, rng=rng)

    @property
    def exports_dir(self) -> Path:
        return self.project_dir / "exports"

    def stage_config(self, stage: dict[str, Any] | None) -> dict[str, Any]:
        """Merged RL config with stage reward/termination/command overrides."""
        if not stage:
            return self.rl_config
        merged = dict(self.rl_config)
        task = dict(merged.get("task") or {})
        task["reward_terms"] = stage.get("reward_terms") or task.get("reward_terms") or []
        task["termination"] = stage.get("termination") or task.get("termination") or {}
        merged["task"] = task
        merged["stage"] = stage
        merged["command"] = stage.get("command") or {}
        merged["disturbance"] = stage.get("disturbance") or {}
        return merged


def _geo_spawn_export_path(exports: Path, project_name: str) -> Path:
    return exports / f"geo_{project_name}_default_pose.yaml"


def _load_geo_spawn_export(exports: Path, project_name: str) -> dict[str, Any]:
    path = _geo_spawn_export_path(exports, project_name)
    if not path.is_file():
        return {}
    return load_yaml(path)


def _apply_spawn_joints_to_gains(joint_gains: dict[str, JointGains], spawn_doc: dict[str, Any]) -> None:
    joints = spawn_doc.get("joints") or {}
    for name, val in joints.items():
        if name in joint_gains:
            joint_gains[name].default_position = float(val)


def _joint_names_from_controllers(doc: dict[str, Any]) -> list[str]:
    jtc = doc.get("joint_trajectory_controller") or {}
    params = jtc.get("ros__parameters") or {}
    joints = params.get("joints") or []
    return [str(j) for j in joints]


def _parse_gains(doc: dict[str, Any], joint_names: list[str]) -> dict[str, JointGains]:
    joints_block = doc.get("joints") or {}
    out: dict[str, JointGains] = {}
    for name in joint_names:
        raw = joints_block.get(name) or {}
        out[name] = JointGains(
            name=name,
            kp=float(raw.get("kp", 20.0)),
            kd=float(raw.get("kd", 0.5)),
            default_position=float(raw.get("default_position", 0.0)),
            action_scale=float(raw.get("action_scale", 0.25)),
            effort_limit=float(raw.get("effort_limit", 80.0)),
            velocity_limit=float(raw.get("velocity_limit", 10.0)),
        )
    return out


def _sanitize_pkg(name: str) -> str:
    import re

    n = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
    n = re.sub(r"_+", "_", n).strip("_")
    if not n or n[0].isdigit():
        n = f"robot_{n or 'unnamed'}"
    return n


def load_project_artifacts(
    project_dir: Path,
    *,
    rl_config: dict[str, Any] | None = None,
) -> ProjectArtifacts:
    project_dir = project_dir.expanduser().resolve()
    project_name = project_dir.name
    exports = project_dir / "exports"

    if rl_config is None:
        rl_path = exports / f"rl_{project_name}_config.yaml"
        if not rl_path.is_file():
            raise FileNotFoundError(f"Missing RL config: {rl_path}")
        rl_config = merge_ppo_into_rl(load_yaml(rl_path), project_dir)

    env_block = rl_config.get("env") or {}
    obs_file = env_block.get("observations_file") or f"sens_{project_name}_observations.yaml"
    gains_file = env_block.get("gains_file") or f"ctrl_{project_name}_gains.yaml"

    obs_path = exports / Path(obs_file).name
    gains_path = exports / Path(gains_file).name
    ctrl_path = exports / f"ctrl_{project_name}_controllers.yaml"

    observations_doc = load_yaml(obs_path) if obs_path.is_file() else {"observations": {}}
    gains_doc = load_yaml(gains_path) if gains_path.is_file() else {"joints": {}}
    controllers_doc = load_yaml(ctrl_path) if ctrl_path.is_file() else {}

    joint_names = _joint_names_from_controllers(controllers_doc)
    if not joint_names:
        joint_names = list((gains_doc.get("joints") or {}).keys())
    if not joint_names:
        joint_names = [f"joint_{i}" for i in range(12)]

    joint_gains = _parse_gains(gains_doc, joint_names)

    spawn_export = _load_geo_spawn_export(exports, project_name)
    if spawn_export:
        _apply_spawn_joints_to_gains(joint_gains, spawn_export)

    control = observations_doc.get("control") or {}
    ctrl_yaml_name = control.get("controllers_yaml") or f"ctrl_{project_name}_controllers.yaml"
    if not controllers_doc and (exports / ctrl_yaml_name).is_file():
        controllers_doc = load_yaml(exports / ctrl_yaml_name)
        joint_names = _joint_names_from_controllers(controllers_doc) or joint_names
        joint_gains = _parse_gains(gains_doc, joint_names)

    ws_setup = project_dir / "workspace" / "install" / "setup.bash"
    workspace_setup = ws_setup if ws_setup.is_file() else None
    pkg = _sanitize_pkg(project_name)

    hp = rl_config.get("hyperparameters") or {}
    control_dt = float(hp.get("control_dt", rl_config.get("control_dt", 0.02)))

    offset = _offset_from_doc(spawn_export)
    base_spawn = _base_spawn_from_doc(spawn_export, offset)
    spawn_config = _effective_spawn(base_spawn, offset)

    return ProjectArtifacts(
        project_dir=project_dir,
        project_name=project_name,
        rl_config=rl_config,
        observations_doc=observations_doc,
        controllers_doc=controllers_doc,
        gains_doc=gains_doc,
        joint_names=joint_names,
        joint_gains=joint_gains,
        control_dt=control_dt,
        workspace_setup=workspace_setup,
        bringup_pkg=f"{pkg}_bringup",
        base_spawn=base_spawn,
        spawn_offset=offset,
        spawn_config=spawn_config,
    )
