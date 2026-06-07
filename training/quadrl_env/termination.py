"""Episode termination and truncation from RL Trainer export."""
from __future__ import annotations

from typing import Any

import numpy as np

from quadrl_env.sim_state import SimState
from quadrl_env.standing_heights import (
    FALL_DROP_MARGIN_M,
    PLACEHOLDER_BODY_HEIGHT_M,
    fall_threshold_for_target,
)


def _optional_positive_float(d: dict[str, Any], key: str, *, default: float) -> float | None:
    """Threshold from config, or None when disabled (null / 0 / negative)."""
    if key not in d:
        return default
    val = d[key]
    if val is None:
        return None
    f = float(val)
    return f if f > 0 else None


class TerminationEngine:
    def __init__(self, termination: dict[str, Any]) -> None:
        self._termination = termination or {}
        self._terms = [t for t in (self._termination.get("termination_terms") or []) if t.get("enabled", True)]
        self._fall_h_override: float | None = None

    @property
    def max_episode_steps(self) -> int:
        return int(self._termination.get("max_episode_steps", 1000))

    @property
    def grace_steps(self) -> int:
        """Steps after reset during which fall/tilt/safety checks are suppressed.

        The robot is teleported on reset and needs a few control steps for the
        pose to settle and for IMU/odom to publish valid frames. Checking
        fall_height/max_tilt on step 1 against transient sensor values terminates
        otherwise-healthy episodes immediately. Timeout still applies (it is
        checked before the grace short-circuit). Default 0 = unchanged behavior.
        """
        return int(self._termination.get("termination_grace_steps", 0))

    def resolve_fall_threshold(self, standing_height: float | None) -> dict[str, Any]:
        """Anchor the fall-height threshold to the robot's actual standing height.

        A curriculum exported with the generic ``PLACEHOLDER_BODY_HEIGHT_M`` instead
        of this robot's real grounded height can carry a fall threshold *above* where
        the robot spawns, which terminates every episode on step 1
        (``reason=fall_height``) and makes learning impossible. Guard against that:
        when the configured threshold is not strictly below the standing height,
        derive it from the standing height and the standard drop margin instead.
        Sane configs (threshold already below the standing height) are kept as-is.

        Returns a dict describing the resolution so the caller can warn on a
        correction. Idempotent; call once per env after construction.
        """
        raw = self._termination.get("fall_base_height_threshold")
        configured = float(raw) if raw is not None else None
        if standing_height is None:
            self._fall_h_override = (
                configured if configured is not None
                else fall_threshold_for_target(PLACEHOLDER_BODY_HEIGHT_M)
            )
            return {"effective": self._fall_h_override, "configured": configured, "corrected": False}
        canonical = round(float(standing_height) - FALL_DROP_MARGIN_M, 4)
        if configured is None or configured >= float(standing_height):
            self._fall_h_override = canonical
            return {"effective": canonical, "configured": configured, "corrected": configured is not None}
        self._fall_h_override = configured
        return {"effective": configured, "configured": configured, "corrected": False}

    def check(
        self,
        state: SimState,
        *,
        step_reward: float,
        cumulative_reward: float,
        command: dict[str, Any] | None = None,
    ) -> tuple[bool, bool, str]:
        """Return (terminated, truncated, reason)."""
        if state.episode_step >= self.max_episode_steps:
            if self._termination.get("timeout_truncation", True):
                return False, True, "timeout"
            return True, False, "timeout"

        if state.episode_step <= self.grace_steps:
            return False, False, ""

        fall_h = self._fall_h_override
        if fall_h is None:
            fall_h = float(
                self._termination.get(
                    "fall_base_height_threshold",
                    fall_threshold_for_target(PLACEHOLDER_BODY_HEIGHT_M),
                )
            )
        if state.base_height < fall_h:
            return True, False, "fall_height"

        max_tilt = float(self._termination.get("max_tilt_rad", 1.2))
        if state.tilt_rad > max_tilt:
            return True, False, "max_tilt"

        max_torque = _optional_positive_float(self._termination, "max_joint_torque", default=200.0)
        if max_torque is not None:
            est_torque = float(np.max(np.abs(state.joint_vel))) * 10.0
            if est_torque > max_torque:
                return True, False, "max_joint_torque"

        nominal_h = float((command or {}).get("target_body_height", PLACEHOLDER_BODY_HEIGHT_M))

        for term in self._terms:
            reason = self._check_term(
                term,
                state,
                step_reward=step_reward,
                cumulative_reward=cumulative_reward,
                nominal_body_height=nominal_h,
            )
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
        nominal_body_height: float = PLACEHOLDER_BODY_HEIGHT_M,
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
            nominal = float(params.get("nominal_body_height", nominal_body_height))
            if abs(state.base_height - nominal) > max_dev and state.num_contacts < int(
                params.get("min_terrain_contacts", 1)
            ):
                return "height_deviation"
        if tid == "reward_anomaly":
            if step_reward > float(params.get("max_step_reward", 5.0)):
                return "reward_spike"
            if cumulative_reward > float(params.get("cumulative_threshold", 100.0)):
                return "reward_cumulative"
        return ""
