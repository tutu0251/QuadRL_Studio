"""Lightweight quadruped simulator for training without ROS/Gazebo."""
from __future__ import annotations

import math
import random
from typing import Any

import numpy as np

from quadrl_env.disturbances import DisturbanceEngine
from quadrl_env.project_config import JointGains, ProjectArtifacts
from quadrl_env.sim_state import SimState


class MockSimBackend:
    """Integrates joint targets toward commanded velocities for reward shaping tests and CI."""

    def __init__(self, artifacts: ProjectArtifacts, *, seed: int | None = None) -> None:
        self._artifacts = artifacts
        self._rng = random.Random(seed)
        self._n = len(artifacts.joint_names)
        self._foot_keys = _foot_keys_from_observations(artifacts.observations_doc)
        self._disturbance = DisturbanceEngine({})
        self.reset()

    def set_stage_context(
        self,
        *,
        command: dict[str, Any] | None = None,
        disturbance: dict[str, Any] | None = None,
    ) -> None:
        if command is not None:
            self._command = dict(command)
        self._disturbance = DisturbanceEngine(disturbance)

    def default_joint_positions(self) -> np.ndarray:
        return np.array(
            [self._artifacts.joint_gains[n].default_position for n in self._artifacts.joint_names],
            dtype=np.float32,
        )

    def reset(self, *, command: dict[str, Any] | None = None) -> SimState:
        if command:
            self._command = command
        elif not hasattr(self, "_command"):
            self._command = {}
        self._step = 0
        self._disturbance.reset()
        self._joint_pos = self.default_joint_positions()
        self._joint_vel = np.zeros(self._n, dtype=np.float32)
        self._base_height = float(self._command.get("target_body_height", 0.35))
        self._base_lin = np.zeros(3, dtype=np.float32)
        self._base_ang = np.zeros(3, dtype=np.float32)
        self._gravity = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        self._contacts = {k: 40.0 for k in self._foot_keys}
        self._air_time = {k: 0.0 for k in self._foot_keys}
        return self._state()

    def step(self, target_positions: np.ndarray, *, command: dict[str, Any] | None = None) -> SimState:
        if command:
            self._command = command
        dt = self._artifacts.control_dt
        self._step += 1

        error = target_positions - self._joint_pos
        self._joint_vel = 0.7 * self._joint_vel + 0.3 * error / max(dt, 1e-3)
        self._joint_pos = self._joint_pos + self._joint_vel * dt

        cmd_vx = float(self._command.get("target_lin_vel_x", 0))
        cmd_vy = float(self._command.get("target_lin_vel_y", 0))
        cmd_wz = float(self._command.get("target_ang_vel_z", 0))
        target_h = float(self._command.get("target_body_height", 0.35))

        self._base_lin[0] += 0.15 * (cmd_vx - self._base_lin[0])
        self._base_lin[1] += 0.15 * (cmd_vy - self._base_lin[1])
        self._base_ang[2] += 0.15 * (cmd_wz - self._base_ang[2])
        self._base_height += 0.1 * (target_h - self._base_height)

        noise = self._rng.uniform(-0.02, 0.02)
        tilt = abs(noise) + 0.05 * float(np.linalg.norm(self._joint_vel))
        self._gravity = np.array([tilt, 0.0, -math.sqrt(max(0.0, 1.0 - tilt * tilt))], dtype=np.float32)

        for k in self._foot_keys:
            self._contacts[k] = 30.0 + 10.0 * self._rng.random()
            self._air_time[k] = 0.05 + 0.1 * self._rng.random()

        state = self._state()
        return self._disturbance.apply_mock(state)

    def action_to_targets(self, action: np.ndarray) -> np.ndarray:
        targets = np.zeros(self._n, dtype=np.float32)
        for i, name in enumerate(self._artifacts.joint_names):
            g = self._artifacts.joint_gains.get(name) or JointGains(name=name)
            a = float(action[i]) if i < len(action) else 0.0
            targets[i] = g.default_position + a * g.action_scale
        return targets

    def _state(self) -> SimState:
        return SimState(
            joint_pos=self._joint_pos.copy(),
            joint_vel=self._joint_vel.copy(),
            base_lin_vel=self._base_lin.copy(),
            base_ang_vel=self._base_ang.copy(),
            projected_gravity=self._gravity.copy(),
            base_height=float(self._base_height),
            contact_forces=dict(self._contacts),
            foot_air_time=dict(self._air_time),
            episode_step=self._step,
        )


def _foot_keys_from_observations(doc: dict[str, Any]) -> list[str]:
    keys = []
    for key, spec in (doc.get("observations") or {}).items():
        if (spec.get("kind") or "").lower() == "contact":
            keys.append(key)
    return keys or ["fl_contact", "fr_contact", "rl_contact", "rr_contact"]
