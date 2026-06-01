"""Episode termination and truncation from RL Trainer export."""
from __future__ import annotations

from typing import Any

import numpy as np

from quadrl_env.sim_state import SimState


class TerminationEngine:
    def __init__(self, termination: dict[str, Any]) -> None:
        self._termination = termination or {}
        self._terms = [t for t in (self._termination.get("termination_terms") or []) if t.get("enabled", True)]

    @property
    def max_episode_steps(self) -> int:
        return int(self._termination.get("max_episode_steps", 1000))

    def check(
        self,
        state: SimState,
        *,
        step_reward: float,
        cumulative_reward: float,
    ) -> tuple[bool, bool, str]:
        """Return (terminated, truncated, reason)."""
        if state.episode_step >= self.max_episode_steps:
            if self._termination.get("timeout_truncation", True):
                return False, True, "timeout"
            return True, False, "timeout"

        fall_h = float(self._termination.get("fall_base_height_threshold", 0.12))
        if state.base_height < fall_h:
            return True, False, "fall_height"

        max_tilt = float(self._termination.get("max_tilt_rad", 1.2))
        if state.tilt_rad > max_tilt:
            return True, False, "max_tilt"

        max_torque = float(self._termination.get("max_joint_torque", 200.0))
        est_torque = float(np.max(np.abs(state.joint_vel))) * 10.0
        if est_torque > max_torque:
            return True, False, "max_joint_torque"

        for term in self._terms:
            reason = self._check_term(term, state, step_reward=step_reward, cumulative_reward=cumulative_reward)
            if reason:
                return True, False, reason

        return False, False, ""

    def _check_term(
        self,
        term: dict[str, Any],
        state: SimState,
        *,
        step_reward: float,
        cumulative_reward: float,
    ) -> str:
        tid = term.get("id", "")
        params = term.get("params") or {}

        if tid == "foot_slip_contact_loss":
            min_c = int(params.get("min_contacts", 1))
            if state.num_contacts < min_c and state.episode_step > 5:
                return "contact_loss"
        if tid == "base_linear_velocity_limit":
            max_v = float(params.get("max_lin_vel", 3.0))
            if float(np.linalg.norm(state.base_lin_vel)) > max_v:
                return "base_lin_vel"
        if tid == "base_angular_velocity_limit":
            max_w = float(params.get("max_ang_vel", 5.0))
            if float(np.linalg.norm(state.base_ang_vel)) > max_w:
                return "base_ang_vel"
        if tid == "height_deviation_terrain_contact":
            max_dev = float(params.get("max_height_deviation", 0.12))
            if abs(state.base_height - 0.35) > max_dev and state.num_contacts < int(params.get("min_terrain_contacts", 1)):
                return "height_deviation"
        if tid == "reward_anomaly":
            if step_reward > float(params.get("max_step_reward", 5.0)):
                return "reward_spike"
            if cumulative_reward > float(params.get("cumulative_threshold", 100.0)):
                return "reward_cumulative"
        return ""
