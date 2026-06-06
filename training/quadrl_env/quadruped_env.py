"""Gymnasium environment for quadruped RL from QuadRL exports."""
from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from quadrl_env.observations import ObservationBuilder
from quadrl_env.project_config import ProjectArtifacts
from quadrl_env.rewards import RewardEngine
from quadrl_env.ros_sim import RosSimBackend
from quadrl_env.termination import TerminationEngine


class QuadrupedEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        artifacts: ProjectArtifacts,
        *,
        stage: dict[str, Any] | None = None,
        env_id: int = 0,
    ) -> None:
        super().__init__()
        self._artifacts = artifacts
        self._stage = stage
        self._env_id = env_id
        self._config = artifacts.stage_config(stage)
        self._command = dict(self._config.get("command") or (stage or {}).get("command") or {})
        self._disturbance = dict(
            self._config.get("disturbance") or (stage or {}).get("disturbance") or {}
        )

        task = self._config.get("task") or {}
        self._reward_engine = RewardEngine(task.get("reward_terms") or [])
        self._termination = TerminationEngine(task.get("termination") or {})
        self._anchor_fall_threshold()

        self._obs_builder = ObservationBuilder(
            self._config,
            artifacts.observations_doc,
            artifacts.joint_names,
        )

        n_joints = len(artifacts.joint_names)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(n_joints,), dtype=np.float32)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self._obs_builder.observation_dim,),
            dtype=np.float32,
        )

        self._sim = RosSimBackend(artifacts, env_id=env_id)
        self._sim.set_stage_context(command=self._command, disturbance=self._disturbance)

        self._last_action = np.zeros(n_joints, dtype=np.float32)
        self._cumulative_reward = 0.0
        self._state = None
        self._episode_returns: list[float] = []
        self._fall_count = 0
        self._episode_count = 0

    def _anchor_fall_threshold(self) -> None:
        """Tie the fall-height threshold to this robot's real grounded spawn height.

        Prevents a leaked placeholder standing height from putting the threshold
        above where the robot spawns (which would terminate every episode on step 1).
        """
        base = getattr(self._artifacts, "base_spawn", None)
        standing_h = float(base["z"]) if isinstance(base, dict) and base.get("z") is not None else None
        info = self._termination.resolve_fall_threshold(standing_h)
        if info.get("corrected") and self._env_id == 0:
            print(
                "[train] WARNING: configured fall_base_height_threshold="
                f"{info['configured']} is not below the spawn height {standing_h}; "
                f"using {info['effective']} (spawn height - drop margin) instead. "
                "This usually means the curriculum was exported with the placeholder "
                "standing height rather than this robot's real height_policy.",
                flush=True,
            )

    def close(self) -> None:
        if isinstance(self._sim, RosSimBackend):
            self._sim.close()
        super().close()

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        self._last_action.fill(0.0)
        self._cumulative_reward = 0.0
        self._sim.set_stage_context(command=self._command, disturbance=self._disturbance)
        self._state = self._sim.reset(command=self._command)
        obs = self._build_obs()
        return obs, self._info_dict(0.0, False, False, "")

    def step(self, action: np.ndarray):
        action = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        targets = self._sim.action_to_targets(action)
        self._state = self._sim.step(targets, command=self._command)
        reward, components = self._reward_engine.compute(
            self._state,
            command=self._command,
            action=action,
            last_action=self._last_action,
        )
        self._cumulative_reward += reward
        terminated, truncated, reason = self._termination.check(
            self._state,
            step_reward=reward,
            cumulative_reward=self._cumulative_reward,
            command=self._command,
        )
        if terminated and reason in ("fall_height", "max_tilt", "contact_loss"):
            self._fall_count += 1

        self._last_action = action.copy()
        obs = self._build_obs()
        if terminated or truncated:
            self._episode_returns.append(self._cumulative_reward)
            self._episode_count += 1

        info = self._info_dict(reward, terminated, truncated, reason)
        info["reward_components"] = components
        return obs, reward, terminated, truncated, info

    def _build_obs(self) -> np.ndarray:
        sensor_vectors = {}
        if isinstance(self._sim, RosSimBackend):
            sensor_vectors = self._sim.sensor_vectors()
        return self._obs_builder.build(
            self._state,
            command=self._command,
            last_action=self._last_action,
            sensor_vectors=sensor_vectors,
        )

    def _info_dict(self, reward: float, terminated: bool, truncated: bool, reason: str) -> dict[str, Any]:
        return {
            "reward": reward,
            "cumulative_reward": self._cumulative_reward,
            "terminated": terminated,
            "truncated": truncated,
            "termination_reason": reason,
            "command": dict(self._command),
            "episode_step": self._state.episode_step if self._state else 0,
            "fall_rate": self._fall_count / max(self._episode_count, 1),
            "mean_episode_reward": float(np.mean(self._episode_returns[-20:])) if self._episode_returns else 0.0,
            "mean_episode_length_frac": (
                self._state.episode_step / max(self._termination.max_episode_steps, 1) if self._state else 0.0
            ),
        }
