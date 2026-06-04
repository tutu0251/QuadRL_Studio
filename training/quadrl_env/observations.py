"""Build policy observation vectors from RL + sensor exports."""
from __future__ import annotations

from typing import Any

import numpy as np

from quadrl_env.sensor_packing import fit_dim, sensor_term_dim
from quadrl_env.sim_state import SimState
from quadrl_env.standing_heights import PLACEHOLDER_BODY_HEIGHT_M


def _normalize(value: float, *, scale: float, offset: float, clip_min: float | None, clip_max: float | None) -> float:
    if scale == 0:
        scale = 1.0
    x = (value - offset) / scale
    if clip_min is not None:
        x = max(clip_min, x)
    if clip_max is not None:
        x = min(clip_max, x)
    return float(x)


def _normalize_vec(
    arr: np.ndarray,
    *,
    scale: float,
    offset: float,
    clip_min: float | None,
    clip_max: float | None,
) -> np.ndarray:
    if scale == 0:
        scale = 1.0
    out = (arr - offset) / scale
    if clip_min is not None:
        out = np.maximum(out, clip_min)
    if clip_max is not None:
        out = np.minimum(out, clip_max)
    return out.astype(np.float32)


class ObservationBuilder:
    def __init__(self, rl_config: dict[str, Any], observations_doc: dict[str, Any], joint_names: list[str]) -> None:
        self._joint_index = {n: i for i, n in enumerate(joint_names)}
        self._n_joints = len(joint_names)
        terms = (rl_config.get("observations") or {}).get("terms") or []
        self._terms = [t for t in terms if t.get("enabled", True) and t.get("available", True)]
        if not self._terms:
            self._terms = _default_terms()
        self._sensor_doc = observations_doc.get("observations") or {}
        self.observation_dim = self._compute_dim()

    def _compute_dim(self) -> int:
        total = 0
        for term in self._terms:
            total += self._term_dim(term)
        return max(total, 1)

    def _term_dim(self, term: dict[str, Any]) -> int:
        tid = term.get("id", "")
        if tid == "joint_positions":
            return self._n_joints
        if tid == "joint_velocities":
            return self._n_joints
        if tid == "last_actions":
            return self._n_joints
        if tid == "commands":
            return 5
        if tid in ("base_lin_vel", "base_ang_vel", "projected_gravity"):
            return 3
        if term.get("source") == "sensor":
            key = term.get("key") or ""
            sens = self._sensor_doc.get(key) or {}
            fields = term.get("fields") or sens.get("fields") or []
            kind = (term.get("kind") or sens.get("kind") or "").lower()
            return sensor_term_dim(kind, list(fields))
        return 1

    def build(
        self,
        state: SimState,
        *,
        command: dict[str, Any],
        last_action: np.ndarray,
        sensor_vectors: dict[str, np.ndarray] | None = None,
    ) -> np.ndarray:
        sensor_vectors = sensor_vectors or {}
        parts: list[np.ndarray] = []
        for term in self._terms:
            parts.append(self._build_term(term, state, command=command, last_action=last_action, sensor_vectors=sensor_vectors))
        if not parts:
            return np.zeros(1, dtype=np.float32)
        return np.concatenate(parts).astype(np.float32)

    def _build_term(
        self,
        term: dict[str, Any],
        state: SimState,
        *,
        command: dict[str, Any],
        last_action: np.ndarray,
        sensor_vectors: dict[str, np.ndarray],
    ) -> np.ndarray:
        scale = float(term.get("scale", 1.0))
        offset = float(term.get("offset", 0.0))
        clip_min = term.get("clip_min")
        clip_max = term.get("clip_max")
        tid = term.get("id", "")

        if tid == "joint_positions":
            return _normalize_vec(state.joint_pos, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)
        if tid == "joint_velocities":
            return _normalize_vec(state.joint_vel, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)
        if tid == "last_actions":
            la = last_action if last_action.size == state.joint_pos.size else np.zeros(state.joint_pos.size)
            return _normalize_vec(la, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)
        if tid == "commands":
            cmd = np.array(
                [
                    float(command.get("target_lin_vel_x", 0)),
                    float(command.get("target_lin_vel_y", 0)),
                    float(command.get("target_ang_vel_z", 0)),
                    float(command.get("target_body_height", PLACEHOLDER_BODY_HEIGHT_M)),
                    float(command.get("gait_speed_scale", 1.0)),
                ],
                dtype=np.float32,
            )
            return _normalize_vec(cmd, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)
        if tid == "base_lin_vel":
            return _normalize_vec(state.base_lin_vel, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)
        if tid == "base_ang_vel":
            return _normalize_vec(state.base_ang_vel, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)
        if tid == "projected_gravity":
            return _normalize_vec(state.projected_gravity, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)

        if term.get("source") == "sensor":
            key = term.get("key") or ""
            expected = self._term_dim(term)
            vec = fit_dim(sensor_vectors.get(key), expected)
            return _normalize_vec(vec, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)

        return np.array([_normalize(0.0, scale=scale, offset=offset, clip_min=clip_min, clip_max=clip_max)], dtype=np.float32)


def _default_terms() -> list[dict[str, Any]]:
    return [
        {"id": "joint_positions", "enabled": True, "available": True, "scale": 2.0, "offset": 0.0, "clip_min": -1.0, "clip_max": 1.0},
        {"id": "joint_velocities", "enabled": True, "available": True, "scale": 6.0, "offset": 0.0, "clip_min": -1.0, "clip_max": 1.0},
        {"id": "base_lin_vel", "enabled": True, "available": True, "scale": 2.0, "offset": 0.0, "clip_min": -1.0, "clip_max": 1.0},
        {"id": "base_ang_vel", "enabled": True, "available": True, "scale": 8.0, "offset": 0.0, "clip_min": -1.0, "clip_max": 1.0},
        {"id": "projected_gravity", "enabled": True, "available": True, "scale": 1.0, "offset": 0.0},
        {"id": "commands", "enabled": True, "available": True, "scale": 1.0, "offset": 0.0, "clip_min": -1.0, "clip_max": 1.0},
        {"id": "last_actions", "enabled": True, "available": True, "scale": 1.0, "offset": 0.0, "clip_min": -1.0, "clip_max": 1.0},
    ]
