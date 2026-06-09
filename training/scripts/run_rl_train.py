#!/usr/bin/env python3
"""Run PPO training from rl_<project>_config.yaml (SB3 + QuadRL quadruped env)."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
from pathlib import Path

import yaml

_TRAINING_ROOT = Path(__file__).resolve().parents[1]
if str(_TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_TRAINING_ROOT))

_shutdown_requested = False


def _install_shutdown_handlers() -> None:
    def _handler(signum: int, frame: object | None) -> None:
        del signum, frame
        global _shutdown_requested
        _shutdown_requested = True

    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)


def _is_ros_shutdown_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if name in ("RCLError", "ExternalShutdownException"):
        return True
    msg = str(exc).lower()
    return "context is invalid" in msg or "rcl_shutdown" in msg


def _prepend_callback(callbacks, first):
    from stable_baselines3.common.callbacks import CallbackList

    if callbacks is None:
        return first
    if isinstance(callbacks, CallbackList):
        return CallbackList([first, *callbacks.callbacks])
    return CallbackList([first, callbacks])


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


def _write_run_manifest(
    run_root: Path,
    project_name: str,
    config_path: Path,
    curriculum: dict,
    *,
    sim_backend: str,
    resume_checkpoint: str | None = None,
    resume_start_stage: int | None = None,
) -> None:
    manifest = {
        "run_id": run_root.name,
        "project": project_name,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "config": str(config_path),
        "tensorboard_logdir": str(run_root),
        "curriculum_enabled": bool(curriculum.get("enabled") and curriculum.get("stages")),
        "sim_backend": sim_backend,
    }
    if resume_checkpoint:
        manifest["resume_checkpoint"] = resume_checkpoint
    if resume_start_stage is not None:
        manifest["resume_start_stage"] = resume_start_stage
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


_MAX_ROS_DOMAIN_ID = 101  # ROS 2 + ROS_LOCALHOST_ONLY safe upper bound

# Resolved once per process and reused for every curriculum stage: the parallel envs of a
# stage reuse the previous stage's still-running Gazebo servers (QUADRL_KEEP_GAZEBO), so the
# domain block must not drift between stages.
_resolved_base_domain_id: int | None = None


def _occupied_ros_domains() -> set[int]:
    """ROS_DOMAIN_IDs currently held by other processes we can see (our own user's procs).

    Two training runs on one host used to both default to base 0 and cross-wire their DDS
    graphs / Gazebo partitions; worse, a hard crash (OOM-kill / ``pkill -9``) can orphan a
    run's Gazebo servers, which keep holding domains 0..N until reaped. Scanning lets the
    next run step around both. We can only read ``environ`` for our own processes — other
    users' sims are invisible and simply skipped (nothing we could deconflict with anyway).
    """
    occupied: set[int] = set()
    my_pid = os.getpid()
    try:
        entries = os.listdir("/proc")
    except OSError:
        return occupied
    prefix = b"ROS_DOMAIN_ID="
    for entry in entries:
        if not entry.isdigit() or int(entry) == my_pid:
            continue
        try:
            with open(f"/proc/{entry}/environ", "rb") as fh:
                raw = fh.read()
        except OSError:
            continue  # process gone, or not ours (EACCES)
        domain: int | None = None
        for field in raw.split(b"\0"):
            if field.startswith(prefix):
                try:
                    domain = int(field[len(prefix) :])
                except ValueError:
                    domain = None
                break
        if domain is None:
            continue
        # The ros2 CLI auto-spawns one long-lived `ros2 daemon` per domain (a shared graph
        # cache, not an exclusive sim resource); it lingers after a run ends. Ignore it, or
        # every successive run would climb to ever-higher domains and exhaust the range.
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as fh:
                cmdline = fh.read()
        except OSError:
            cmdline = b""
        if b"ros2cli.daemon" in cmdline:
            continue
        occupied.add(domain)
    return occupied


def _free_domain_block(num_envs: int, occupied: set[int], preferred: int | None) -> int | None:
    """Lowest base whose block [base .. base+num_envs] (train envs + eval) avoids ``occupied``.

    ``preferred`` (an explicitly requested base) is tried first. Returns None if no block
    fits under the safe ceiling.
    """

    def fits(base: int) -> bool:
        if base < 0 or base + num_envs > _MAX_ROS_DOMAIN_ID:
            return False
        return all((base + offset) not in occupied for offset in range(num_envs + 1))

    if preferred is not None and fits(preferred):
        return preferred
    for base in range(0, _MAX_ROS_DOMAIN_ID - num_envs + 1):
        if fits(base):
            return base
    return None


def _base_ros_domain_id(num_envs: int) -> int:
    """Pick this run's base DDS domain, stepping around domains already in use.

    Envs use base..base+num_envs-1; eval uses base+num_envs. The block is chosen to avoid
    domains held by other visible processes (a second concurrent run, or a crashed run's
    orphaned Gazebo servers), so runs no longer all collide on domain 0. An explicit
    ROS_DOMAIN_ID is honoured when its block is free, otherwise it is shifted to a free one.
    Resolved once and cached for the lifetime of the run.
    """
    global _resolved_base_domain_id
    if _resolved_base_domain_id is not None:
        return _resolved_base_domain_id

    raw = os.environ.get("ROS_DOMAIN_ID", "").strip()
    try:
        preferred: int | None = int(raw)
    except ValueError:
        preferred = None
    if preferred is not None and preferred < 0:
        preferred = None

    occupied = _occupied_ros_domains()
    base = _free_domain_block(num_envs, occupied, preferred)

    if base is None:
        # Nothing free under the ceiling; keep the old deterministic behaviour but warn.
        base = preferred if (preferred is not None and preferred + num_envs <= _MAX_ROS_DOMAIN_ID) else 0
        _log(
            f"[warn] No free ROS_DOMAIN_ID block of size {num_envs + 1} under "
            f"{_MAX_ROS_DOMAIN_ID} (in use: {sorted(occupied)}); falling back to base "
            f"{base}. Concurrent runs may collide — set ROS_DOMAIN_ID to a free value."
        )
    elif preferred is not None and base != preferred:
        clash = sorted(d for d in occupied if preferred <= d <= preferred + num_envs)
        _log(
            f"[warn] Requested ROS_DOMAIN_ID base {preferred} overlaps in-use domains "
            f"{clash}; shifted to free base {base} (domains {base}..{base + num_envs})."
        )
    elif occupied:
        _log(
            f"[train] ROS_DOMAIN_ID base {base} (domains {base}..{base + num_envs}); "
            f"stepped around in-use {sorted(occupied)}."
        )

    _resolved_base_domain_id = base
    return base


def _make_vec_env(
    project_dir: Path,
    config: dict,
    stage: dict | None,
    num_envs: int,
    *,
    base_domain_id: int,
):
    from stable_baselines3.common.vec_env import (
        DummyVecEnv,
        SubprocVecEnv,
        VecMonitor,
    )

    from quadrl_env.env_factory import make_vec_env_fn, resolve_sim_backend

    resolve_sim_backend(project_dir)
    num_envs = max(1, num_envs)

    if num_envs == 1:
        _log("[train] Sim backend: ros (num_envs=1, dummy vec env)")
        fns = [make_vec_env_fn(project_dir, config, stage=stage, env_id=0)]
        return VecMonitor(DummyVecEnv(fns))

    last = base_domain_id + num_envs - 1
    _log(
        f"[train] Sim backend: ros (num_envs={num_envs}, subproc vec env, "
        f"one Gazebo per env on ROS_DOMAIN_ID {base_domain_id}..{last})"
    )
    fns = [
        make_vec_env_fn(
            project_dir,
            config,
            stage=stage,
            env_id=i,
            ros_domain_id=base_domain_id + i,
        )
        for i in range(num_envs)
    ]
    # 'spawn' (not fork): rclpy and its executor thread are not fork-safe.
    return VecMonitor(SubprocVecEnv(fns, start_method="spawn"))


def _make_eval_vec_env(
    project_dir: Path,
    config: dict,
    stage: dict | None,
    *,
    env_id: int,
    ros_domain_id: int | None,
):
    """Eval env with distinct env_id (and DDS domain when parallel) so it does not
    collide with the train envs."""
    from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor

    from quadrl_env.env_factory import make_vec_env_fn, resolve_sim_backend

    resolve_sim_backend(project_dir)
    fns = [
        make_vec_env_fn(
            project_dir,
            config,
            stage=stage,
            env_id=env_id,
            ros_domain_id=ros_domain_id,
        )
    ]
    return VecMonitor(DummyVecEnv(fns))


def _build_learn_callbacks(
    config: dict,
    checkpoint_dir: Path,
    stage: dict | None,
    *,
    eval_env,
    num_envs: int,
):
    from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback

    callbacks = []

    ckpt = config.get("checkpoint") or {}
    if ckpt.get("enabled", True):
        frequency = str(ckpt.get("frequency", "end_only"))
        if frequency in ("steps", "rollout"):
            hp = config.get("hyperparameters") or {}
            n_steps = int(hp.get("n_steps", 2048))
            freq_steps = int(ckpt.get("frequency_steps", 50_000))
            if frequency == "rollout":
                freq_steps = max(1, n_steps * num_envs)
            prefix = _checkpoint_basename(config, stage)
            callbacks.append(
                CheckpointCallback(
                    save_freq=max(1, freq_steps),
                    save_path=str(checkpoint_dir),
                    name_prefix=prefix,
                    save_replay_buffer=False,
                    save_vecnormalize=False,
                )
            )

    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    try:
        from tb_callbacks import build_tensorboard_callbacks

        callbacks.extend(
            build_tensorboard_callbacks(
                config,
                eval_env=eval_env,
                stage=stage,
                num_envs=num_envs,
            )
        )
    except ImportError as exc:
        _log(f"[warn] TensorBoard callbacks unavailable: {exc}")

    if not callbacks:
        return None
    if len(callbacks) == 1:
        return callbacks[0]
    return CallbackList(callbacks)


def _make_stop_training_callback():
    from stable_baselines3.common.callbacks import BaseCallback

    class StopTrainingCallback(BaseCallback):
        def _on_step(self) -> bool:
            return not _shutdown_requested

    return StopTrainingCallback(verbose=0)


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


def _resolve_resume_checkpoint(
    config: dict,
    project_root: Path,
    resume_override: str | None,
) -> Path | None:
    """Return checkpoint path to load, or None for scratch training."""
    resume_ckpt = resume_override if resume_override is not None else (config.get("training") or {}).get("resume_checkpoint")
    if not resume_ckpt:
        return None
    resume_path = Path(resume_ckpt)
    if not resume_path.is_absolute():
        resume_path = project_root / resume_ckpt
    load_path = resume_path if resume_path.is_file() else resume_path.with_suffix(".zip")
    return load_path if load_path.is_file() else None


def _stage_index_for_checkpoint(stages: list, config: dict, ckpt_path: Path) -> int | None:
    """Map a checkpoint file back to the curriculum stage that produced it.

    Stage checkpoints are named ``<basename>.zip`` (final, saved at stage end) or
    ``<basename>_<steps>_steps.zip`` (periodic CheckpointCallback saves), where
    ``<basename>`` comes from :func:`_checkpoint_basename`. Returns the matching
    stage's index in ``stages`` (longest-basename match to avoid prefix
    collisions like ``walk`` vs ``walk_fast``), or ``None`` if nothing matches
    (e.g. a foreign/pretrained checkpoint or the ``best_model`` copy).
    """
    stem = ckpt_path.stem
    best_i: int | None = None
    best_len = -1
    for i, stage in enumerate(stages):
        base = _checkpoint_basename(config, stage)
        if re.fullmatch(re.escape(base) + r"(?:_\d+_steps)?", stem) and len(base) > best_len:
            best_len = len(base)
            best_i = i
    return best_i


def _checkpoint_num_timesteps(path: Path) -> int | None:
    """Best-effort read of an SB3 checkpoint's cumulative timestep count.

    Reads the ``num_timesteps`` field from the zip's ``data`` member without
    loading the model (no env needed). Returns ``None`` if it can't be read,
    in which case callers should fall back to letting SB3 figure out the
    remaining steps at ``learn()`` time.
    """
    import json
    import zipfile

    try:
        with zipfile.ZipFile(path) as zf:
            with zf.open("data") as handle:
                data = json.load(handle)
        value = data.get("num_timesteps")
        return int(value) if value is not None else None
    except Exception:
        return None


def _resolve_start_stage_override(
    curriculum_enabled: bool,
    stages: list,
    resume_ckpt_path: Path | None,
    start_stage: int,
    reset_policy: bool = False,
) -> tuple[int, Path | None, bool]:
    """Validate an explicit ``--start-stage`` request and return the resume plan
    ``(resume_start_i, resume_seed_path, resume_seed_continue)``.

    The chosen stage is seeded with the resume checkpoint's weights and trained
    from a fresh budget (``resume_seed_continue=False``), unlike the filename-based
    auto-detection which may continue an in-progress stage. When ``reset_policy`` is
    set the stage is instead started from a fresh policy (``resume_seed_path=None``),
    so no resume checkpoint is required. Raises ``ValueError`` with a user-facing
    message when the request is invalid.
    """
    if not curriculum_enabled:
        raise ValueError("--start-stage requires a curriculum config")
    if not (0 <= start_stage < len(stages)):
        raise ValueError(
            f"--start-stage {start_stage} out of range (0..{len(stages) - 1})"
        )
    if reset_policy:
        # Fresh policy at the start stage — nothing to seed from.
        return start_stage, None, False
    if resume_ckpt_path is None:
        raise ValueError("--start-stage requires a --resume checkpoint to seed the stage")
    return start_stage, resume_ckpt_path, False


def _train_stage_sb3(
    config: dict,
    stage: dict | None,
    timesteps: int,
    checkpoint_dir: Path,
    run_root: Path,
    project_dir: Path,
    *,
    curriculum: bool,
    resume_override: str | None = None,
    reset_policy: bool = False,
    reset_log_std: float | None = None,
    continue_timesteps: bool = False,
) -> None:
    from stable_baselines3 import PPO

    _install_shutdown_handlers()

    hp = config.get("hyperparameters") or {}
    parallel = config.get("parallel") or {}
    num_envs = max(1, int(parallel.get("num_envs", 1)))
    vec_env_type = str(parallel.get("vec_env_type", "subproc")).lower()
    if num_envs > 1 and vec_env_type == "dummy":
        _log(
            "[warn] vec_env_type=dummy cannot isolate per-env ROS graphs in one process — "
            "using subproc (one Gazebo per env) for num_envs>1"
        )

    base_domain_id = _base_ros_domain_id(num_envs)
    if num_envs > 1:
        # Each env runs its own Gazebo; confine cleanup to each env's own launch group
        # so one env closing does not pkill the others. Set before subprocs spawn so
        # they inherit it.
        os.environ["QUADRL_GAZEBO_SCOPED_CLEANUP"] = "1"

    env = _make_vec_env(project_dir, config, stage, num_envs, base_domain_id=base_domain_id)
    eval_domain_id = base_domain_id + num_envs if num_envs > 1 else None
    eval_env = _make_eval_vec_env(
        project_dir,
        config,
        stage,
        env_id=num_envs,
        ros_domain_id=eval_domain_id,
    )

    device = str(config.get("device", "auto"))
    if device == "auto":
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    tb_dir = _tensorboard_stage_dir(run_root, stage, curriculum=curriculum)
    _log(f"[train] TensorBoard log dir: {tb_dir}")

    project_root = run_root.parent.parent
    load_path = None if reset_policy else _resolve_resume_checkpoint(config, project_root, resume_override)

    if load_path:
        _log(f"[train] Resuming from checkpoint: {load_path}")
        model = PPO.load(str(load_path), env=env, device=device, tensorboard_log=str(tb_dir))
        if reset_log_std is not None:
            # The loaded policy's action-std has already decayed to a near-greedy
            # value, trapping it in a half-speed local optimum that ent_coef can't
            # escape. Overwrite log_std with a fresh exploration value (keeping the
            # learned mean/value weights) so the stage explores again without
            # relearning balance.
            import math

            import torch

            with torch.no_grad():
                model.policy.log_std.data.fill_(float(reset_log_std))
            _log(
                f"[train] Reset policy log_std to {float(reset_log_std):.3f} "
                f"(std≈{math.exp(float(reset_log_std)):.3f}) — exploration restored"
            )
        if continue_timesteps:
            done = int(getattr(model, "num_timesteps", 0))
            remaining = max(0, timesteps - done)
            _log(
                f"[train] Continuing stage from step {done:,} toward target {timesteps:,} "
                f"({remaining:,} remaining)"
            )
    else:
        requested = resume_override or (config.get("training") or {}).get("resume_checkpoint")
        if requested and not reset_policy:
            _log(f"[warn] Resume checkpoint not found: {requested} — training from scratch")
        else:
            _log("[train] Training from scratch")
        # Build policy_kwargs from hyperparameters: net_arch and the initial
        # policy log-std. log_std_init controls how noisy stochastic rollouts are
        # — the SB3 default of 0.0 (std=1.0) makes early rollouts topple a balanced
        # robot in a few steps even when the deterministic policy stands fine.
        policy_kwargs = {}
        net_arch = hp.get("net_arch")
        if net_arch:
            policy_kwargs["net_arch"] = [int(x) for x in net_arch]
        if hp.get("log_std_init") is not None:
            policy_kwargs["log_std_init"] = float(hp["log_std_init"])
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=float(hp.get("learning_rate", 3e-4)),
            n_steps=int(hp.get("n_steps", 2048)),
            batch_size=int(hp.get("batch_size", 64)),
            n_epochs=int(hp.get("n_epochs", 10)),
            gamma=float(hp.get("gamma", 0.99)),
            gae_lambda=float(hp.get("gae_lambda", 0.95)),
            clip_range=float(hp.get("clip_range", 0.2)),
            ent_coef=float(hp.get("ent_coef", 0.0)),
            vf_coef=float(hp.get("vf_coef", 0.5)),
            max_grad_norm=float(hp.get("max_grad_norm", 0.5)),
            policy_kwargs=policy_kwargs or None,
            verbose=1,
            device=device,
            tensorboard_log=str(tb_dir),
        )

    stage_label = stage.get("name", "training") if stage else "training"
    _log(f"[train] PPO learn: {stage_label} ({timesteps:,} timesteps)")
    progress_bar = _use_progress_bar()
    if not progress_bar:
        _log("[train] progress_bar disabled (install tqdm and rich for a live bar)")
    callbacks = _prepend_callback(
        _build_learn_callbacks(
            config,
            checkpoint_dir,
            stage,
            eval_env=eval_env,
            num_envs=num_envs,
        ),
        _make_stop_training_callback(),
    )
    try:
        model.learn(
            total_timesteps=timesteps,
            progress_bar=progress_bar,
            callback=callbacks,
            reset_num_timesteps=not continue_timesteps,
        )
    except Exception as exc:
        if not (_shutdown_requested or _is_ros_shutdown_error(exc)):
            raise
        _log("[train] Training interrupted during shutdown")
    finally:
        env.close()
        eval_env.close()

    if _shutdown_requested:
        return

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
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Override resume checkpoint path (relative to project root or absolute)",
    )
    parser.add_argument(
        "--start-stage",
        type=int,
        default=None,
        help=(
            "Curriculum stage index (0-based) to restart from, seeding it with the "
            "--resume checkpoint's weights and a fresh timestep budget. Overrides the "
            "automatic stage detection. Requires --resume and a curriculum config."
        ),
    )
    parser.add_argument(
        "--reset-policy",
        action="store_true",
        help=(
            "Start the --start-stage stage with a FRESH policy instead of seeding it "
            "from a checkpoint. The policy is rebuilt from scratch (random weights, "
            "log_std_init from the PPO config), restoring full exploration so the stage "
            "can escape a half-speed local optimum a resumed policy is stuck in. No "
            "--resume checkpoint is needed. Requires --start-stage and a curriculum config."
        ),
    )
    parser.add_argument(
        "--reset-log-std",
        nargs="?",
        type=str,
        const="__default__",
        default=None,
        metavar="VALUE",
        help=(
            "After loading the resume/seed checkpoint, reset ONLY the policy's "
            "log_std parameter to VALUE (keeping the learned mean/value weights), "
            "restoring exploration so a converged low-std policy can escape a "
            "half-speed local optimum without relearning balance. Pass a float to "
            "set it explicitly, or omit the value to use the PPO config's "
            "log_std_init. Applies to the stage that loads the checkpoint."
        ),
    )
    parser.add_argument(
        "--sim-backend",
        choices=("auto", "ros"),
        default=None,
        help="Simulation backend (default: QUADRL_SIM_BACKEND or auto; requires ROS workspace)",
    )
    gazebo_mode = parser.add_mutually_exclusive_group()
    gazebo_mode.add_argument(
        "--gazebo-headless",
        action="store_true",
        default=None,
        help="Run Gazebo server-only, no GUI window (default)",
    )
    gazebo_mode.add_argument(
        "--gazebo-gui",
        action="store_true",
        help="Run Gazebo with GUI to watch the robot during training (requires DISPLAY)",
    )
    args = parser.parse_args()
    _install_shutdown_handlers()

    if args.sim_backend:
        os.environ["QUADRL_SIM_BACKEND"] = args.sim_backend
    if args.gazebo_gui:
        os.environ["QUADRL_GAZEBO_HEADLESS"] = "0"
        from quadrl_env.display import ensure_display_for_gui

        ensure_display_for_gui()
    elif args.gazebo_headless or os.environ.get("QUADRL_GAZEBO_HEADLESS") is None:
        os.environ["QUADRL_GAZEBO_HEADLESS"] = "1"

    project_dir = args.project_dir.expanduser().resolve()

    sim_mode = (args.sim_backend or os.environ.get("QUADRL_SIM_BACKEND", "auto")).lower()
    from quadrl_env.ros_env import bootstrap_ros_runtime

    ws_setup = project_dir / "workspace" / "install" / "setup.bash"
    bootstrap_ros_runtime(
        workspace_setup=ws_setup if ws_setup.is_file() else None,
        sim_mode=sim_mode,
    )
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
    curriculum_stages = (
        sorted(curriculum["stages"], key=lambda s: s.get("order", 0)) if curriculum_enabled else []
    )

    from quadrl_env.env_factory import resolve_sim_backend

    sim_backend = resolve_sim_backend(project_dir)

    # Resolve the resume checkpoint and, for curriculum runs, figure out which
    # stage to continue from so we pick up mid-curriculum instead of replaying
    # every stage. The stage and step position are derived from the checkpoint
    # itself: its filename identifies the stage, its embedded num_timesteps gives
    # the position within that stage's budget.
    resume_ckpt_path = _resolve_resume_checkpoint(config, project_dir, args.resume)
    resume_start_i = 0          # index of the first stage to actually run
    resume_seed_path: Path | None = None   # checkpoint to load into that stage
    resume_seed_continue = False           # True => continue that stage's step counter
    reset_start_policy = False             # True => fresh policy at resume_start_i
    if args.reset_policy and args.start_stage is None:
        _log("[error] --reset-policy requires --start-stage")
        return 1
    # Resolve --reset-log-std: None => no reset; "__default__" => use the PPO
    # config's log_std_init; otherwise the explicit float. Reset needs a loaded
    # checkpoint to act on, so it's meaningless with --reset-policy (a fresh
    # policy already uses log_std_init).
    reset_log_std: float | None = None
    if args.reset_log_std is not None:
        if args.reset_policy:
            _log(
                "[warn] --reset-log-std ignored with --reset-policy "
                "(a fresh policy already starts at log_std_init)"
            )
        else:
            if args.reset_log_std == "__default__":
                hp = config.get("hyperparameters") or {}
                if hp.get("log_std_init") is None:
                    _log(
                        "[warn] --reset-log-std given without a value and no "
                        "log_std_init in config — defaulting to -1.0 (std≈0.37)"
                    )
                reset_log_std = float(hp.get("log_std_init", -1.0))
            else:
                try:
                    reset_log_std = float(args.reset_log_std)
                except ValueError:
                    _log(
                        f"[error] --reset-log-std value '{args.reset_log_std}' "
                        "is not a number"
                    )
                    return 1
    if args.start_stage is not None:
        # Explicit "start from stage" mode: skip stages before the chosen index,
        # seed the chosen stage with the checkpoint's weights, and train it from a
        # fresh budget. Overrides the filename-based auto-detection below. With
        # --reset-policy the chosen stage instead starts from a fresh, high-exploration
        # policy (no checkpoint seed).
        try:
            resume_start_i, resume_seed_path, resume_seed_continue = _resolve_start_stage_override(
                curriculum_enabled,
                curriculum_stages,
                resume_ckpt_path,
                args.start_stage,
                reset_policy=args.reset_policy,
            )
        except ValueError as exc:
            _log(f"[error] {exc}")
            return 1
        reset_start_policy = args.reset_policy
    elif resume_ckpt_path and curriculum_enabled:
        matched = _stage_index_for_checkpoint(curriculum_stages, config, resume_ckpt_path)
        if matched is None:
            _log(
                f"[warn] Resume checkpoint '{resume_ckpt_path.name}' does not match any "
                "curriculum stage — seeding stage 1 with it (fresh budget)"
            )
            resume_seed_path = resume_ckpt_path
        else:
            budget = int(curriculum_stages[matched].get("timesteps", 100_000))
            done = _checkpoint_num_timesteps(resume_ckpt_path)
            if done is not None and done >= budget:
                # That stage is already finished — continue from the next stage,
                # seeding it from this checkpoint the same way load_previous does.
                resume_start_i = matched + 1
                resume_seed_path = resume_ckpt_path
                resume_seed_continue = False
            else:
                # Mid-stage: continue this stage's step counter toward its budget.
                resume_start_i = matched
                resume_seed_path = resume_ckpt_path
                resume_seed_continue = True

    _write_run_manifest(
        run_root,
        project_name,
        config_path,
        curriculum,
        sim_backend=sim_backend,
        resume_checkpoint=str(resume_ckpt_path) if resume_ckpt_path else None,
        resume_start_stage=(resume_start_i + 1)
        if ((resume_ckpt_path or reset_start_policy) and curriculum_enabled)
        else None,
    )

    _log(f"[train] Project: {project_name}")
    _log(f"[train] Config: {config_path}")
    _log(f"[train] Algorithm: {config.get('algorithm', 'PPO')} / {config.get('framework', '')}")
    _log(f"[train] Sim backend: {sim_backend}")
    gazebo_headless = os.environ.get("QUADRL_GAZEBO_HEADLESS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    _log(f"[train] Gazebo: {'headless' if gazebo_headless else 'gui'}")
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

    load_prev = bool(curriculum.get("load_previous_checkpoint", True))
    reset_on_advance = bool(curriculum.get("reset_policy_on_stage_advance", False))

    if curriculum_enabled:
        os.environ["QUADRL_KEEP_GAZEBO"] = "1"
        _log("[train] Curriculum enabled — reusing one Gazebo session across stages")
        stages = curriculum_stages
        _log(f"[train] Curriculum: {curriculum.get('name', '')} ({len(stages)} stages)")
        if reset_start_policy and resume_start_i > 0:
            _log(
                f"[train] Fresh-policy restart at stage {resume_start_i + 1}/{len(stages)} "
                f"({stages[resume_start_i].get('name')}) — stages 1..{resume_start_i} skipped; "
                "policy rebuilt from scratch with full exploration (log_std_init from PPO config)"
            )
        elif resume_seed_path is not None and resume_start_i >= len(stages):
            _log(
                f"[train] Resume checkpoint {resume_seed_path.name} completes the final stage "
                "— nothing left to train"
            )
        elif resume_seed_path is not None and resume_start_i > 0:
            _log(
                f"[train] Resuming curriculum at stage {resume_start_i + 1}/{len(stages)} "
                f"from {resume_seed_path.name} — stages 1..{resume_start_i} already complete (skipped)"
            )
        prev_ckpt: Path | None = None
        for i, stage in enumerate(stages):
            if _shutdown_requested:
                break
            if i < resume_start_i:
                # Completed in a previous run — keep its checkpoint as the
                # carry-forward source but don't retrain it.
                prev_ckpt = checkpoint_dir / _checkpoint_basename(config, stage)
                _log(
                    f"[train] === Stage {i + 1}/{len(stages)}: {stage.get('name')} "
                    "— already complete, skipping ==="
                )
                continue
            _log(f"[train] === Stage {i + 1}/{len(stages)}: {stage.get('name')} ===")
            cmd = stage.get("command") or {}
            _log(
                f"[train] Command vel: lin={cmd.get('target_lin_vel_x', 0)} "
                f"ang={cmd.get('target_ang_vel_z', 0)}"
            )
            continue_timesteps = False
            if i == resume_start_i and reset_start_policy:
                # Fresh-policy restart: rebuild the policy from scratch at this stage
                # (full exploration via log_std_init) and ignore any carry-forward
                # checkpoint, so the resumed low-std weights can't sneak back in.
                resume = None
                reset_policy = True
            elif i == resume_start_i and resume_seed_path is not None:
                resume = str(resume_seed_path)
                continue_timesteps = resume_seed_continue
                # Never wipe the policy on the stage we are resuming into.
                reset_policy = False if resume_seed_continue else (reset_on_advance and i > 0)
            else:
                resume = None
                if i > 0 and load_prev and prev_ckpt and prev_ckpt.is_file():
                    resume = str(prev_ckpt)
                reset_policy = reset_on_advance and i > 0
            # Only reset exploration on the stage that loads the seed checkpoint —
            # later stages that carry forward a checkpoint should keep their std.
            stage_reset_log_std = (
                reset_log_std
                if (i == resume_start_i and resume_seed_path is not None)
                else None
            )
            if use_sb3:
                _train_stage_sb3(
                    config,
                    stage,
                    int(stage.get("timesteps", 100_000)),
                    checkpoint_dir,
                    run_root,
                    project_dir,
                    curriculum=True,
                    resume_override=resume,
                    reset_policy=reset_policy,
                    reset_log_std=stage_reset_log_std,
                    continue_timesteps=continue_timesteps,
                )
                prev_ckpt = checkpoint_dir / _checkpoint_basename(config, stage)
            else:
                _dry_run_stage(
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
        if use_sb3:
            _train_stage_sb3(
                config,
                None,
                total,
                checkpoint_dir,
                run_root,
                project_dir,
                curriculum=False,
                resume_override=args.resume,
                reset_log_std=reset_log_std,
            )
        else:
            _dry_run_stage(config, None, total, checkpoint_dir, run_root, curriculum=False)

    if _shutdown_requested:
        _log("[train] Training stopped by user")
        return 0

    _log("[train] Training finished successfully")
    return 0


if __name__ == "__main__":
    exit_code = 0
    try:
        exit_code = main()
    finally:
        try:
            from quadrl_env.ros_sim import shutdown_shared_gazebo

            # Final cleanup runs in the main process after all env subprocesses have
            # exited, so a host-wide sweep is safe again — drop the scoped flag to
            # reap any Gazebo strays parallel workers left behind.
            os.environ.pop("QUADRL_GAZEBO_SCOPED_CLEANUP", None)
            shutdown_shared_gazebo()
        except Exception:
            pass
    sys.exit(exit_code)
