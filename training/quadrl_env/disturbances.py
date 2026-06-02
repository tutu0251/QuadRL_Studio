"""Apply curriculum disturbance settings during simulation steps."""
from __future__ import annotations

import random
from typing import Any

import numpy as np

from quadrl_env.sim_state import SimState


class DisturbanceEngine:
    def __init__(self, disturbance: dict[str, Any] | None) -> None:
        self._cfg = disturbance or {}
        self._rng = random.Random()
        self._step = 0
        self._next_push = self._interval()

    def reset(self, *, seed: int | None = None) -> None:
        if seed is not None:
            self._rng = random.Random(seed)
        self._step = 0
        self._next_push = self._interval()

    @property
    def enabled(self) -> bool:
        return bool(self._cfg.get("enabled", False))

    def _interval(self) -> int:
        interval = int(self._cfg.get("push_interval_steps", 500))
        return max(1, interval)

    def apply_mock(self, state: SimState) -> SimState:
        if not self.enabled:
            return state
        self._step += 1
        if self._step < self._next_push:
            return state
        self._next_push = self._step + self._interval()

        push_n = float(self._cfg.get("push_force_n", 0.0))
        lateral_n = float(self._cfg.get("lateral_impulse_n", 0.0))
        orient_noise = float(self._cfg.get("random_orientation_noise_rad", 0.0))

        if push_n > 0:
            angle = self._rng.uniform(0, 2 * np.pi)
            impulse = push_n * 0.02
            state.base_lin_vel[0] += impulse * float(np.cos(angle))
            state.base_lin_vel[1] += impulse * float(np.sin(angle))

        if lateral_n > 0:
            state.base_lin_vel[1] += lateral_n * 0.01 * self._rng.choice([-1.0, 1.0])

        if orient_noise > 0:
            tilt = orient_noise * self._rng.uniform(-1.0, 1.0)
            g = state.projected_gravity.copy()
            g[0] += tilt
            norm = float(np.linalg.norm(g))
            if norm > 1e-6:
                state.projected_gravity = (g / norm).astype(np.float32)

        return state

    def ros_wrench(self) -> tuple[np.ndarray, np.ndarray] | None:
        """Return (force_xyz, torque_xyz) in world frame, or None if no push this step."""
        if not self.enabled:
            return None
        self._step += 1
        if self._step < self._next_push:
            return None
        self._next_push = self._step + self._interval()

        push_n = float(self._cfg.get("push_force_n", 0.0))
        lateral_n = float(self._cfg.get("lateral_impulse_n", 0.0))
        if push_n <= 0 and lateral_n <= 0:
            return None

        angle = self._rng.uniform(0, 2 * np.pi)
        fx = push_n * float(np.cos(angle)) if push_n > 0 else 0.0
        fy = (push_n * float(np.sin(angle)) if push_n > 0 else 0.0) + (
            lateral_n * self._rng.choice([-1.0, 1.0]) if lateral_n > 0 else 0.0
        )
        return np.array([fx, fy, 0.0], dtype=np.float64), np.zeros(3, dtype=np.float64)
