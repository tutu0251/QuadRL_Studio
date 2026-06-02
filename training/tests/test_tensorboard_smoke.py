"""Smoke test: SB3 learn() writes TensorBoard event files (requires ROS workspace)."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = REPO / "training" / "scripts" / "run_rl_train.py"
PYTHON = REPO / "training" / ".venv" / "bin" / "python"


def _minimal_config(project_name: str) -> dict:
    return {
        "algorithm": "PPO",
        "framework": "stable_baselines3",
        "project": project_name,
        "device": "cpu",
        "hyperparameters": {"total_timesteps": 512, "n_steps": 64, "batch_size": 32},
        "parallel": {"num_envs": 1},
        "curriculum": {"enabled": False},
        "observations": {
            "terms": [
                {"id": "joint_positions", "enabled": True, "available": True, "scale": 2.0, "clip_min": -1, "clip_max": 1},
                {"id": "commands", "enabled": True, "available": True, "scale": 1.0},
            ]
        },
        "task": {
            "reward_terms": [{"id": "alive", "type": "reward", "enabled": True, "weight": 0.25, "params": {}}],
            "termination": {"max_episode_steps": 200, "fall_base_height_threshold": 0.08, "max_tilt_rad": 1.5},
        },
        "logging": {
            "success_reward_threshold": 0.5,
            "eval": {"enabled": True, "eval_freq": 128, "n_eval_episodes": 2},
            "policy_histograms": {"enabled": True, "freq": 256},
        },
    }


def _write_control_exports(exports: Path, name: str) -> None:
    (exports / f"ctrl_{name}_controllers.yaml").write_text(
        "joint_trajectory_controller:\n  ros__parameters:\n    joints: [j1, j2]\n",
        encoding="utf-8",
    )
    (exports / f"ctrl_{name}_gains.yaml").write_text(
        "joints:\n  j1:\n    default_position: 0\n    action_scale: 0.2\n  j2:\n    default_position: 0\n    action_scale: 0.2\n",
        encoding="utf-8",
    )
    (exports / f"sens_{name}_observations.yaml").write_text("observations: {}\n", encoding="utf-8")


@pytest.mark.skipif(
    os.environ.get("QUADRL_INTEGRATION") != "1",
    reason="Set QUADRL_INTEGRATION=1 with a built ROS workspace to run end-to-end training smoke test",
)
def test_learn_writes_tensorboard_events():
    if not PYTHON.is_file():
        pytest.skip("training venv not installed")

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "demo_bot"
        exports = project_dir / "exports"
        exports.mkdir(parents=True)
        _write_control_exports(exports, "demo_bot")
        config_path = exports / "rl_demo_bot_config.yaml"
        config_path.write_text(yaml.dump(_minimal_config("demo_bot")), encoding="utf-8")
        env = os.environ.copy()
        env["QUADRL_SIM_BACKEND"] = "ros"

        proc = subprocess.run(
            [str(PYTHON), str(TRAIN_SCRIPT), str(project_dir), "--config", str(config_path)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(REPO),
            env=env,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout

        runs = project_dir / "runs"
        assert runs.is_dir()
        run_dirs = list(runs.iterdir())
        assert run_dirs
        run_root = run_dirs[0]
        assert (run_root / "run_info.yaml").is_file()

        events = list(run_root.rglob("events.out.tfevents.*"))
        assert events, f"no TensorBoard events under {run_root}"

        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

        tags: set[str] = set()
        seen_logdirs: set[str] = set()
        for event_path in events:
            logdir = str(event_path.parent)
            if logdir in seen_logdirs:
                continue
            seen_logdirs.add(logdir)
            acc = EventAccumulator(logdir, size_guidance={"scalars": 500})
            acc.Reload()
            tags.update(acc.Tags().get("scalars", []))
        assert "rollout/ep_rew_std" in tags or "rollout/success_rate" in tags, (
            f"expected fundamental rollout stats, got: {sorted(tags)[:20]}"
        )
        assert any(t.startswith("eval/") for t in tags), f"expected eval/* scalars, got: {sorted(tags)[:20]}"


if __name__ == "__main__":
    test_learn_writes_tensorboard_events()
    print("SMOKE OK")
