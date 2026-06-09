"""Shaped reward terms from RL Trainer export (reward catalog semantics).

Sign/scale convention (important): every term returns a value in ``[0, 1]``.

* Reward terms return ``1`` at the optimum and decay toward ``0`` (Gaussian on the
  error). With a positive weight they only ever *add* reward.
* Penalty terms return ``0`` when the robot is behaving and rise toward ``1`` as the
  undesired quantity grows. With a negative weight they only ever *subtract*, bounded
  by ``|weight|``.

Keeping both families on the same ``[0, 1]`` scale is what makes the catalog weights
(``reward_catalog.py``) meaningful: a penalty can never dwarf the rewards and drag the
episode return below zero on its own. Penalties used to return raw, unbounded physical
magnitudes (``sum(joint_pos**2)``, ``std(contact_forces)`` in newtons, ...), which is
why a perfectly-posed robot still accrued large negative reward.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from quadrl_env.sim_state import SimState
from quadrl_env.standing_heights import PLACEHOLDER_BODY_HEIGHT_M


def _gaussian_sq(err: float, sigma: float) -> float:
    """Closeness in [0, 1]: 1 when err==0, decaying to 0 as |err| grows."""
    sigma = max(sigma, 1e-6)
    return math.exp(-0.5 * (err / sigma) ** 2)


def _gaussian_penalty(err: float, sigma: float) -> float:
    """Bounded badness in [0, 1]: 0 when err==0, approaching 1 as |err| grows."""
    return 1.0 - _gaussian_sq(err, sigma)


def _rms(values: np.ndarray) -> float:
    """Root-mean-square magnitude — scale stays independent of vector length."""
    if values.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(values))))


class RewardEngine:
    def __init__(
        self,
        reward_terms: list[dict[str, Any]],
        *,
        default_joint_pos: np.ndarray | None = None,
    ) -> None:
        self._terms = [t for t in reward_terms if t.get("enabled", True)]
        self._default_joint_pos = (
            np.asarray(default_joint_pos, dtype=np.float32)
            if default_joint_pos is not None
            else None
        )

    def _joint_deviation(self, joint_pos: np.ndarray) -> np.ndarray:
        """Joint angles relative to the rest/spawn pose.

        The robot's natural pose is bent-legged, so absolute joint angles are large and
        non-zero even when standing perfectly. Posture terms must measure how far the
        robot has drifted *from that rest pose*, otherwise they constantly penalise the
        intended stance. Falls back to absolute angles when no rest pose was provided.
        """
        default = self._default_joint_pos
        if default is None or default.size != joint_pos.size:
            return joint_pos
        return joint_pos - default

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

        # —— Rewards (1 == optimum) ——
        if tid == "alive":
            return 1.0
        if tid == "upright":
            return _gaussian_sq(state.tilt_rad, sigma)
        if tid == "height":
            target = float(params.get("target_height", command.get("target_body_height", PLACEHOLDER_BODY_HEIGHT_M)))
            return _gaussian_sq(state.base_height - target, sigma)
        if tid == "posture":
            dev = self._joint_deviation(state.joint_pos)
            return _gaussian_sq(_rms(dev), sigma)
        if tid == "contact":
            min_c = int(params.get("min_contacts", 2))
            err = max(0.0, min_c - state.num_contacts)
            return _gaussian_sq(err, sigma)
        if tid == "forward_tracking":
            target = float(command.get("target_lin_vel_x", 0))
            return _gaussian_sq(float(state.base_lin_vel[0]) - target, sigma)
        if tid == "forward_progress":
            # Linear forward-velocity reward: ramps 0 -> 1 as vx goes 0 -> target,
            # clipped so standing earns 0, moving backward earns 0, and exceeding
            # target earns no bonus (forward_tracking handles precise matching).
            # Unlike the Gaussian forward_tracking it has no plateau at vx=0, so it
            # supplies a constant gradient off the "balance in place" optimum.
            target = float(command.get("target_lin_vel_x", 0)) or 1.0
            vx = float(state.base_lin_vel[0])
            return max(0.0, min(vx, target)) / abs(target)
        if tid == "lateral_tracking":
            target = float(command.get("target_lin_vel_y", 0))
            return _gaussian_sq(float(state.base_lin_vel[1]) - target, sigma)
        if tid == "yaw_tracking":
            target = float(command.get("target_ang_vel_z", 0))
            return _gaussian_sq(float(state.base_ang_vel[2]) - target, sigma)
        if tid == "diagonal_balance":
            return _gaussian_sq(_contact_force_imbalance(state), sigma)
        if tid == "air_time":
            target = float(params.get("target_air_time", 0.12))
            at = list(state.foot_air_time.values()) or [0.0]
            err = abs(float(np.mean(at)) - target)
            return _gaussian_sq(err, sigma)
        if tid == "foot_clearance":
            return 0.0

        # —— Penalties (0 == no penalty, bounded to 1) ——
        if tid == "angular_velocity":
            return _gaussian_penalty(float(np.linalg.norm(state.base_ang_vel)), sigma)
        if tid == "linear_velocity":
            vy = float(state.base_lin_vel[1])
            vz = float(state.base_lin_vel[2])
            return _gaussian_penalty(math.sqrt(vy * vy + vz * vz), sigma)
        if tid == "z_velocity":
            return _gaussian_penalty(abs(float(state.base_lin_vel[2])), sigma)
        if tid == "joint_velocity":
            return _gaussian_penalty(_rms(state.joint_vel), sigma)
        if tid == "action_velocity" or tid == "action_rate" or tid == "smoothness":
            return _gaussian_penalty(_rms(action - last_action), sigma)
        if tid in ("posture_penalty", "target_posture"):
            dev = self._joint_deviation(state.joint_pos)
            return _gaussian_penalty(_rms(dev), sigma)
        if tid == "contact_balance":
            return _gaussian_penalty(_contact_force_imbalance(state), sigma)
        if tid == "contact_switch":
            return 0.0
        if tid == "target_like":
            vx = float(state.base_lin_vel[0]) - float(command.get("target_lin_vel_x", 0))
            wz = float(state.base_ang_vel[2]) - float(command.get("target_ang_vel_z", 0))
            return _gaussian_penalty(math.sqrt(vx * vx + wz * wz), sigma)
        if tid == "stumble":
            threshold = float(params.get("threshold", 35.0))
            max_f = max(state.contact_forces.values()) if state.contact_forces else 0.0
            return _gaussian_penalty(max(0.0, max_f - threshold), sigma)
        if tid == "slip":
            threshold = float(params.get("threshold", 0.25))
            mean_abs = float(np.mean(np.abs(state.joint_vel))) if state.joint_vel.size else 0.0
            return _gaussian_penalty(max(0.0, mean_abs - threshold), sigma)
        if tid == "zmp":
            margin = float(params.get("margin", 0.02))
            return _gaussian_penalty(max(0.0, state.tilt_rad - margin), sigma)
        return 0.0


def _contact_force_imbalance(state: SimState) -> float:
    """Spread of foot contact forces, normalised to ~[0, 1] by the peak force.

    Raw force std (newtons) used to feed both the diagonal-balance reward and the
    contact-balance penalty directly, which saturated them against the Gaussian sigmas
    (and the simulator currently reports binary 0/peak contact forces, so the raw std is
    tens of newtons). Dividing by the peak force keeps the measure scale-free and
    meaningful regardless of the underlying force magnitude.
    """
    forces = list(state.contact_forces.values())
    if len(forces) < 2:
        return 0.0
    peak = max(abs(f) for f in forces)
    if peak <= 1e-6:
        return 0.0
    return float(np.std(forces)) / peak
