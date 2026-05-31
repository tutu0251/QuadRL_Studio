#!/usr/bin/env python3
"""Run PPO training from rl_<project>_config.yaml (SB3 + optional curriculum)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import yaml


def _load_config(config_path: Path) -> dict:
    text = config_path.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    if config_path.suffix.lower() == ".json":
        return json.loads(body) or {}
    return yaml.safe_load(body) or {}


def _merge_ppo_config(config: dict, project_dir: Path) -> dict:
    """Overlay PPO hyperparameters and parallel settings from PPO Planner export."""
    ppo_file = config.get("ppo_config_file")
    if not ppo_file:
        return config

    ppo_path = Path(ppo_file)
    if not ppo_path.is_absolute():
        ppo_path = project_dir / "exports" / ppo_file
    if not ppo_path.is_file():
        _log(f"[warn] PPO config not found: {ppo_path}")
        return config

    ppo = _load_config(ppo_path)
    merged = dict(config)
    for key in ("hyperparameters", "parallel", "device", "checkpoint", "best_model"):
        if key in ppo:
            merged[key] = ppo[key]
    return merged


def _log(msg: str) -> None:
    print(msg, flush=True)


def _use_progress_bar() -> bool:
    try:
        import tqdm  # noqa: F401
        import rich  # noqa: F401
        return True
    except ImportError:
        return False


def _run_timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _safe_segment(value: str, *, max_len: int = 32) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", str(value).strip()).strip("_")
    return (cleaned or "stage")[:max_len]


def _tensorboard_stage_dir(run_root: Path, stage: dict | None, *, curriculum: bool) -> Path:
    if curriculum and stage:
        order = int(stage.get("order", 0))
        sid = _safe_segment(stage.get("id", "stage"))
        name = _safe_segment(stage.get("name", sid))
        sub = f"{order:02d}_{sid}_{name}"
    else:
        sub = "training"
    stage_dir = run_root / sub
    stage_dir.mkdir(parents=True, exist_ok=True)
    return stage_dir


def _write_run_manifest(run_root: Path, project_name: str, config_path: Path, curriculum: dict) -> None:
    manifest = {
        "run_id": run_root.name,
        "project": project_name,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "config": str(config_path),
        "tensorboard_logdir": str(run_root),
        "curriculum_enabled": bool(curriculum.get("enabled") and curriculum.get("stages")),
    }
    (run_root / "run_info.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _checkpoint_dir(project_dir: Path, config: dict) -> Path:
    ckpt = config.get("checkpoint") or {}
    rel = str(ckpt.get("directory", "checkpoints")).strip() or "checkpoints"
    path = (project_dir / rel).resolve()
    if project_dir.resolve() not in path.parents and path != project_dir.resolve():
        path = project_dir / "checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _checkpoint_basename(config: dict, stage: dict | None) -> str:
    ckpt = config.get("checkpoint") or {}
    template = str(ckpt.get("filename_template", "ppo_{stage_id}"))
    stage_id = stage.get("id", "final") if stage else "final"
    name = template.replace("{stage_id}", str(stage_id))
    return re.sub(r"[^\w\-]+", "_", name).strip("_") or "ppo_final"


def _build_learn_callbacks(config: dict, checkpoint_dir: Path, stage: dict | None) -> list:
    ckpt = config.get("checkpoint") or {}
    if not ckpt.get("enabled", True):
        return []
    frequency = str(ckpt.get("frequency", "end_only"))
    if frequency not in ("steps", "rollout"):
        return []
    try:
        from stable_baselines3.common.callbacks import CheckpointCallback
    except ImportError:
        return []

    hp = config.get("hyperparameters") or {}
    par = config.get("parallel") or {}
    n_steps = int(hp.get("n_steps", 2048))
    num_envs = max(1, int(par.get("num_envs", 1)))
    freq_steps = int(ckpt.get("frequency_steps", 50_000))
    if frequency == "rollout":
        freq_steps = max(1, n_steps * num_envs)
    prefix = _checkpoint_basename(config, stage)
    return [
        CheckpointCallback(
            save_freq=max(1, freq_steps),
            save_path=str(checkpoint_dir),
            name_prefix=prefix,
            save_replay_buffer=False,
            save_vecnormalize=False,
        )
    ]


def _save_best_model_copy(config: dict, checkpoint_dir: Path, source_ckpt: Path) -> None:
    best = config.get("best_model") or {}
    if not best.get("enabled", True):
        return
    rel = str(best.get("directory", "checkpoints")).strip() or "checkpoints"
    best_dir = checkpoint_dir if rel == str(config.get("checkpoint", {}).get("directory", "checkpoints")) else checkpoint_dir.parent / rel
    best_dir.mkdir(parents=True, exist_ok=True)
    filename = str(best.get("filename", "best_model")).strip() or "best_model"
    dest = best_dir / f"{filename}.zip"
    if source_ckpt.with_suffix(".zip").exists():
        dest.write_bytes(source_ckpt.with_suffix(".zip").read_bytes())
        _log(f"[train] Best model copy: {dest} (metric={best.get('metric', 'mean_episode_reward')})")


def _train_stage_sb3(
    config: dict,
    stage: dict | None,
    timesteps: int,
    checkpoint_dir: Path,
    run_root: Path,
    *,
    curriculum: bool,
) -> None:
    import gymnasium as gym
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    hp = config.get("hyperparameters") or {}

    def make_env():
        return gym.make("CartPole-v1")

    env = DummyVecEnv([make_env for _ in range(max(1, (config.get("parallel") or {}).get("num_envs", 1)))])

    device = str(config.get("device", "auto"))
    if device == "auto":
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    tb_dir = _tensorboard_stage_dir(run_root, stage, curriculum=curriculum)
    _log(f"[train] TensorBoard log dir: {tb_dir}")

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=float(hp.get("learning_rate", 3e-4)),
        n_steps=int(hp.get("n_steps", 2048)),
        batch_size=int(hp.get("batch_size", 64)),
        n_epochs=int(hp.get("n_epochs", 10)),
        gamma=float(hp.get("gamma", 0.99)),
        verbose=1,
        device=device,
        tensorboard_log=str(tb_dir),
    )

    training = config.get("training") or {}
    resume_ckpt = training.get("resume_checkpoint")
    if resume_ckpt:
        project_root = run_root.parent.parent
        resume_path = Path(resume_ckpt)
        if not resume_path.is_absolute():
            resume_path = project_root / resume_ckpt
        load_path = resume_path if resume_path.is_file() else resume_path.with_suffix(".zip")
        if load_path.is_file():
            _log(f"[train] Resuming from checkpoint: {load_path}")
            model = PPO.load(str(load_path), env=env, device=device)
        else:
            _log(f"[warn] Resume checkpoint not found: {resume_path} — training from scratch")
    else:
        _log("[train] No resume checkpoint — training from scratch")

    stage_label = stage.get("name", "training") if stage else "training"
    _log(f"[train] PPO learn: {stage_label} ({timesteps:,} timesteps)")
    progress_bar = _use_progress_bar()
    if not progress_bar:
        _log("[train] progress_bar disabled (install tqdm and rich for a live bar)")
    callbacks = _build_learn_callbacks(config, checkpoint_dir, stage)
    model.learn(
        total_timesteps=timesteps,
        progress_bar=progress_bar,
        callback=callbacks or None,
    )
    if not (config.get("checkpoint") or {}).get("enabled", True):
        _log("[train] Checkpoints disabled in config — skipping save")
        return
    ckpt_base = checkpoint_dir / _checkpoint_basename(config, stage)
    model.save(str(ckpt_base))
    _log(f"[train] Checkpoint saved: {ckpt_base}.zip")
    _save_best_model_copy(config, checkpoint_dir, ckpt_base)


def _dry_run_stage(
    config: dict,
    stage: dict | None,
    timesteps: int,
    checkpoint_dir: Path,
    run_root: Path,
    *,
    curriculum: bool,
) -> None:
    label = stage.get("name", "training") if stage else "training"
    tb_dir = _tensorboard_stage_dir(run_root, stage, curriculum=curriculum)
    _log(
        f"[train] Dry-run stage: {label} ({timesteps:,} timesteps) — "
        f"install gymnasium + stable-baselines3 for real training"
    )
    _log(f"[train] TensorBoard log dir (dry-run, no events): {tb_dir}")
    steps = min(timesteps, 50_000)
    chunk = max(1000, steps // 20)
    for done in range(0, steps + 1, chunk):
        _log(f"[train] progress {done:,} / {timesteps:,}")
        time.sleep(0.05)
    ckpt = checkpoint_dir / f"dry_run_{stage.get('id', 'final') if stage else 'final'}.txt"
    ckpt.write_text(f"completed at {time.time()}\n", encoding="utf-8")
    _log(f"[train] Dry-run marker: {ckpt}")


def main() -> int:
    parser = argparse.ArgumentParser(description="QuadRL RL training launcher")
    parser.add_argument("project_dir", type=Path, help="Project folder under quadruped_dev_tool/projects")
    parser.add_argument("--config", type=Path, default=None, help="Override rl config yaml path")
    parser.add_argument("--dry-run", action="store_true", help="Simulate training without SB3")
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    project_name = project_dir.name
    config_path = args.config or (project_dir / "exports" / f"rl_{project_name}_config.yaml")

    if not config_path.is_file():
        _log(f"[error] Missing config: {config_path}")
        return 1

    config = _merge_ppo_config(_load_config(config_path), project_dir)
    checkpoint_dir = _checkpoint_dir(project_dir, config)

    run_root = project_dir / "runs" / _run_timestamp()
    run_root.mkdir(parents=True, exist_ok=True)

    curriculum = config.get("curriculum") or {}
    curriculum_enabled = bool(curriculum.get("enabled") and curriculum.get("stages"))
    _write_run_manifest(run_root, project_name, config_path, curriculum)

    _log(f"[train] Project: {project_name}")
    _log(f"[train] Config: {config_path}")
    _log(f"[train] Algorithm: {config.get('algorithm', 'PPO')} / {config.get('framework', '')}")
    _log(f"[train] TensorBoard run root: {run_root}")
    _log(f"[train] View with: tensorboard --logdir {project_dir / 'runs'}")

    use_sb3 = not args.dry_run
    if use_sb3:
        try:
            import gymnasium  # noqa: F401
            import stable_baselines3  # noqa: F401
        except ImportError:
            _log("[warn] gymnasium/stable-baselines3 not installed — falling back to dry-run")
            use_sb3 = False

    train_fn = _train_stage_sb3 if use_sb3 else _dry_run_stage

    if curriculum_enabled:
        stages = sorted(curriculum["stages"], key=lambda s: s.get("order", 0))
        _log(f"[train] Curriculum: {curriculum.get('name', '')} ({len(stages)} stages)")
        for i, stage in enumerate(stages):
            _log(f"[train] === Stage {i + 1}/{len(stages)}: {stage.get('name')} ===")
            cmd = stage.get("command") or {}
            _log(
                f"[train] Command vel: lin={cmd.get('target_lin_vel_x', 0)} "
                f"ang={cmd.get('target_ang_vel_z', 0)}"
            )
            train_fn(
                config,
                stage,
                int(stage.get("timesteps", 100_000)),
                checkpoint_dir,
                run_root,
                curriculum=True,
            )
    else:
        hp = config.get("hyperparameters") or {}
        total = int(hp.get("total_timesteps", 100_000))
        train_fn(config, None, total, checkpoint_dir, run_root, curriculum=False)

    _log("[train] Training finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
