"""Simulation state snapshot used by observation, reward, and termination engines."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SimState:
    joint_pos: np.ndarray
    joint_vel: np.ndarray
    base_lin_vel: np.ndarray  # body frame (vx, vy, vz)
    base_ang_vel: np.ndarray  # body frame
    projected_gravity: np.ndarray  # unit vector in body frame
    base_height: float
    contact_forces: dict[str, float] = field(default_factory=dict)
    foot_air_time: dict[str, float] = field(default_factory=dict)
    episode_step: int = 0

    @property
    def tilt_rad(self) -> float:
        g = self.projected_gravity
        if g.size < 3:
            return 0.0
        gz = float(np.clip(g[2], -1.0, 1.0))
        return float(np.arccos(abs(gz)))

    @property
    def num_contacts(self) -> int:
        return sum(1 for v in self.contact_forces.values() if v > 1.0)

    def copy(self) -> SimState:
        return SimState(
            joint_pos=self.joint_pos.copy(),
            joint_vel=self.joint_vel.copy(),
            base_lin_vel=self.base_lin_vel.copy(),
            base_ang_vel=self.base_ang_vel.copy(),
            projected_gravity=self.projected_gravity.copy(),
            base_height=self.base_height,
            contact_forces=dict(self.contact_forces),
            foot_air_time=dict(self.foot_air_time),
            episode_step=self.episode_step,
        )
