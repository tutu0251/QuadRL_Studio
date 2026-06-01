"""Smoke test: SB3 learn() writes TensorBoard event files."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

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
        "logging": {
            "eval": {"enabled": True, "eval_freq": 128, "n_eval_episodes": 2},
            "policy_histograms": {"enabled": True, "freq": 256},
        },
    }


def test_learn_writes_tensorboard_events():
    if not PYTHON.is_file():
        return

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "demo_bot"
        exports = project_dir / "exports"
        exports.mkdir(parents=True)
        config_path = exports / "rl_demo_bot_config.yaml"
        config_path.write_text(yaml.dump(_minimal_config("demo_bot")), encoding="utf-8")

        proc = subprocess.run(
            [str(PYTHON), str(TRAIN_SCRIPT), str(project_dir), "--config", str(config_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO),
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
