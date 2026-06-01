"""Shaped reward terms from RL Trainer export (reward catalog semantics)."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from quadrl_env.sim_state import SimState


def _gaussian_sq(err: float, sigma: float) -> float:
    sigma = max(sigma, 1e-6)
    return math.exp(-0.5 * (err / sigma) ** 2)


class RewardEngine:
    def __init__(self, reward_terms: list[dict[str, Any]]) -> None:
        self._terms = [t for t in reward_terms if t.get("enabled", True)]

    def compute(
        self,
        state: SimState,
        *,
        command: dict[str, Any],
        action: np.ndarray,
        last_action: np.ndarray,
    ) -> tuple[float, dict[str, float]]:
        total = 0.0
        components: dict[str, float] = {}
        for term in self._terms:
            val = self._term_value(term, state, command=command, action=action, last_action=last_action)
            weight = float(term.get("weight", 0.0))
            contrib = weight * val
            components[term.get("id", "unknown")] = contrib
            total += contrib
        return float(total), components

    def _term_value(
        self,
        term: dict[str, Any],
        state: SimState,
        *,
        command: dict[str, Any],
        action: np.ndarray,
        last_action: np.ndarray,
    ) -> float:
        tid = term.get("id", "")
        params = term.get("params") or {}
        sigma = float(params.get("sigma", 0.2))

        if tid == "alive":
            return 1.0
        if tid == "upright":
            return _gaussian_sq(state.tilt_rad, sigma)
        if tid == "height":
            target = float(params.get("target_height", command.get("target_body_height", 0.35)))
            return _gaussian_sq(state.base_height - target, sigma)
        if tid == "posture":
            return _gaussian_sq(float(np.linalg.norm(state.joint_pos)), sigma)
        if tid == "contact":
            min_c = int(params.get("min_contacts", 2))
            err = max(0.0, min_c - state.num_contacts)
            return _gaussian_sq(err, sigma)
        if tid == "forward_tracking":
            target = float(command.get("target_lin_vel_x", 0))
            return _gaussian_sq(float(state.base_lin_vel[0]) - target, sigma)
        if tid == "lateral_tracking":
            target = float(command.get("target_lin_vel_y", 0))
            return _gaussian_sq(float(state.base_lin_vel[1]) - target, sigma)
        if tid == "yaw_tracking":
            target = float(command.get("target_ang_vel_z", 0))
            return _gaussian_sq(float(state.base_ang_vel[2]) - target, sigma)
        if tid == "diagonal_balance":
            forces = list(state.contact_forces.values())
            if len(forces) < 2:
                return 0.0
            err = float(np.std(forces))
            return _gaussian_sq(err, sigma)
        if tid == "air_time":
            target = float(params.get("target_air_time", 0.12))
            at = list(state.foot_air_time.values()) or [0.0]
            err = abs(float(np.mean(at)) - target)
            return _gaussian_sq(err, sigma)
        if tid == "foot_clearance":
            return 0.0
        if tid == "angular_velocity":
            return float(np.sum(state.base_ang_vel**2))
        if tid == "linear_velocity":
            vy = float(state.base_lin_vel[1])
            vz = float(state.base_lin_vel[2])
            return vy * vy + vz * vz
        if tid == "z_velocity":
            return float(state.base_lin_vel[2] ** 2)
        if tid == "joint_velocity":
            return float(np.sum(state.joint_vel**2)) / sigma
        if tid == "action_velocity" or tid == "action_rate" or tid == "smoothness":
            delta = action - last_action
            return float(np.sum(delta**2)) / sigma
        if tid in ("posture_penalty", "target_posture"):
            return float(np.sum(state.joint_pos**2))
        if tid == "contact_balance":
            forces = list(state.contact_forces.values())
            if not forces:
                return 1.0
            return float(np.std(forces))
        if tid == "contact_switch":
            return 0.0
        if tid == "target_like":
            vx = float(state.base_lin_vel[0]) - float(command.get("target_lin_vel_x", 0))
            wz = float(state.base_ang_vel[2]) - float(command.get("target_ang_vel_z", 0))
            return vx * vx + wz * wz
        if tid == "stumble":
            threshold = float(params.get("threshold", 35.0))
            max_f = max(state.contact_forces.values()) if state.contact_forces else 0.0
            return max(0.0, max_f - threshold) / sigma
        if tid == "slip":
            return float(np.sum(np.abs(state.joint_vel))) / max(len(state.joint_vel), 1)
        if tid == "zmp":
            return max(0.0, state.tilt_rad - float(params.get("margin", 0.02)))
        return 0.0
