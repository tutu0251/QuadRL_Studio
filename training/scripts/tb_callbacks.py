"""TensorBoard callbacks: eval, rollout stats, policy histograms, hparams."""
from __future__ import annotations

from typing import Any

import numpy as np

from stable_baselines3.common.callbacks import BaseCallback, EvalCallback


def _logging_cfg(config: dict) -> dict:
    return config.get("logging") or {}


def _tb_writer(model) -> Any | None:
    from stable_baselines3.common.logger import TensorBoardOutputFormat

    logger = getattr(model, "logger", None)
    if logger is None:
        return None
    for fmt in logger.output_formats:
        if isinstance(fmt, TensorBoardOutputFormat):
            return fmt.writer
    return None


def _hparam_dict(config: dict, stage: dict | None) -> dict[str, float | str | bool]:
    hp = config.get("hyperparameters") or {}
    par = config.get("parallel") or {}
    out: dict[str, float | str | bool] = {
        "algorithm": str(config.get("algorithm", "PPO")),
        "learning_rate": float(hp.get("learning_rate", 3e-4)),
        "n_steps": float(hp.get("n_steps", 2048)),
        "batch_size": float(hp.get("batch_size", 64)),
        "n_epochs": float(hp.get("n_epochs", 10)),
        "gamma": float(hp.get("gamma", 0.99)),
        "num_envs": float(max(1, int(par.get("num_envs", 1)))),
    }
    if stage:
        out["stage_id"] = str(stage.get("id", ""))
        out["stage_timesteps"] = float(stage.get("timesteps", 0))
        cmd = stage.get("command") or {}
        out["cmd_lin_vel_x"] = float(cmd.get("target_lin_vel_x", 0))
        out["cmd_ang_vel_z"] = float(cmd.get("target_ang_vel_z", 0))
    return out


class HparamsCallback(BaseCallback):
    """Log run hyperparameters to TensorBoard HParams tab (once per stage)."""

    def __init__(self, config: dict, stage: dict | None, verbose: int = 0) -> None:
        super().__init__(verbose)
        self._config = config
        self._stage = stage
        self._done = False

    def _on_training_start(self) -> None:
        if self._done:
            return
        writer = _tb_writer(self.model)
        if writer is None:
            return
        hparams = _hparam_dict(self._config, self._stage)
        try:
            from torch.utils.tensorboard.summary import hparams

            exp, ssi, sei = hparams(hparam_dict=hparams, metric_dict={})
            writer.file_writer.add_summary(exp)
            writer.file_writer.add_summary(ssi)
            writer.file_writer.add_summary(sei)
        except Exception:
            pass
        self._done = True

    def _on_step(self) -> bool:
        return True


class EpisodeStatsCallback(BaseCallback):
    """Extra rollout scalars: min/max/std reward, episode length stats, success rate."""

    def __init__(self, *, success_threshold: float = 499.0, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.success_threshold = success_threshold

    def _on_rollout_end(self) -> None:
        buffer = getattr(self.model, "ep_info_buffer", None)
        if not buffer or len(buffer) == 0:
            return
        rewards = [float(info["r"]) for info in buffer]
        lengths = [float(info["l"]) for info in buffer]
        self.logger.record("rollout/ep_rew_min", float(np.min(rewards)))
        self.logger.record("rollout/ep_rew_max", float(np.max(rewards)))
        self.logger.record("rollout/ep_rew_std", float(np.std(rewards)))
        self.logger.record("rollout/ep_len_min", float(np.min(lengths)))
        self.logger.record("rollout/ep_len_max", float(np.max(lengths)))
        self.logger.record("rollout/ep_len_std", float(np.std(lengths)))
        successes = sum(1 for r in rewards if r >= self.success_threshold)
        self.logger.record("rollout/success_rate", successes / len(rewards))

    def _on_step(self) -> bool:
        return True


class PolicyHistogramCallback(BaseCallback):
    """Log policy MLP weight histograms periodically."""

    def __init__(self, *, log_freq: int = 50_000, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.log_freq = log_freq
        self._last_log = 0

    def _on_step(self) -> bool:
        if self.num_timesteps - self._last_log < self.log_freq:
            return True
        writer = _tb_writer(self.model)
        if writer is None:
            return True
        try:
            import torch
        except ImportError:
            return True
        policy = getattr(self.model, "policy", None)
        if policy is None:
            return True
        for name, param in policy.named_parameters():
            if not isinstance(param, torch.Tensor) or param.ndim < 1:
                continue
            tag = f"policy/{name.replace('.', '/')}"
            writer.add_histogram(tag, param.detach().cpu(), global_step=self.num_timesteps)
        self._last_log = self.num_timesteps
        return True


class MonitorProgressCallback(BaseCallback):
    """Emit structured progress lines for Train Monitor log parsing."""

    def __init__(
        self,
        *,
        stage_name: str,
        total_timesteps: int,
        log_freq_rollouts: int = 1,
        verbose: int = 0,
    ) -> None:
        super().__init__(verbose)
        self._stage_name = stage_name
        self._total_timesteps = max(1, int(total_timesteps))
        self._log_freq_rollouts = max(1, int(log_freq_rollouts))
        self._rollout_count = 0
        self._episode_count = 0
        self._last_term = "-"

    def _on_step(self) -> bool:
        infos = self.locals.get("infos")
        if isinstance(infos, list):
            for info in infos:
                if not isinstance(info, dict):
                    continue
                reason = info.get("termination_reason")
                if reason:
                    self._last_term = str(reason)
                if info.get("episode"):
                    self._episode_count += 1
        return True

    def _on_rollout_end(self) -> None:
        self._rollout_count += 1
        if self._rollout_count % self._log_freq_rollouts != 0:
            return
        done = self.num_timesteps
        total = self._total_timesteps
        print(
            f"[train] stage={self._stage_name} progress={done:,}/{total:,} "
            f"rollout={self._rollout_count} episodes={self._episode_count} "
            f"last_term={self._last_term}",
            flush=True,
        )


def build_tensorboard_callbacks(
    config: dict,
    *,
    eval_env,
    stage: dict | None,
    num_envs: int,
) -> list[BaseCallback]:
    """Return SB3 callbacks that add fundamental TensorBoard series."""
    logging = _logging_cfg(config)
    callbacks: list[BaseCallback] = []

    if logging.get("hparams", True):
        callbacks.append(HparamsCallback(config, stage))

    if logging.get("episode_stats", True):
        threshold = float(logging.get("success_reward_threshold", 499.0))
        callbacks.append(EpisodeStatsCallback(success_threshold=threshold))

    stage_name = stage.get("name", "training") if stage else "training"
    stage_steps = int(stage.get("timesteps", config.get("total_timesteps", 0) or 0)) if stage else int(
        config.get("total_timesteps", 0) or 0
    )
    if stage_steps <= 0:
        par = config.get("parallel") or {}
        hp = config.get("hyperparameters") or {}
        stage_steps = int(hp.get("n_steps", 2048)) * max(1, int(par.get("num_envs", 1)))
    callbacks.append(
        MonitorProgressCallback(stage_name=stage_name, total_timesteps=max(1, stage_steps))
    )

    eval_cfg = logging.get("eval") or {}
    if eval_cfg.get("enabled", True) and eval_env is not None:
        eval_freq = int(eval_cfg.get("eval_freq", 10_000))
        n_eval = int(eval_cfg.get("n_eval_episodes", 5))
        callbacks.append(
            EvalCallback(
                eval_env,
                n_eval_episodes=max(1, n_eval),
                eval_freq=max(1, eval_freq // max(1, num_envs)),
                deterministic=True,
                render=False,
            )
        )

    hist_cfg = logging.get("policy_histograms") or {}
    if hist_cfg.get("enabled", True):
        freq = int(hist_cfg.get("freq", 50_000))
        callbacks.append(PolicyHistogramCallback(log_freq=max(1, freq // max(1, num_envs))))

    return callbacks
