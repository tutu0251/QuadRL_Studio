# RL Trainer Editor

Configure quadruped RL training for **Stable-Baselines3 + ROS 2 / Gazebo**: task rewards/penalties, termination thresholds, PPO hyperparameters, parallel env settings, and custom parameters.

## Quick start

```bash
chmod +x start_*.sh
./start_rl_trainer_editor.sh
```

- Backend API: `http://0.0.0.0:8005`
- Frontend UI: `http://0.0.0.0:5178`

## Prerequisites

Complete the sensor editor pipeline first (`sensor_model.json` and `sens_*_observations.yaml`). The trainer editor reads the same project folder as other QuadRL tools:

`~/quadruped_dev_tool/projects/<name>/`

## Workflow

1. **File → select project** — auto-bootstraps with `velocity_tracking` preset + machine recommendations.
2. **Curriculum** — for step-by-step training, apply **Stand still → Sprint**: stand → slow walk → walk → run → sprint (~2.1M steps total). Each stage has its own rewards, velocity command, and advance criteria.
3. **Recommend** — tune `num_envs`, batch sizes, and device from CPU/RAM/GPU profile.
4. **Rewards / Termination / Hyperparams / Parallel / Custom** — adjust manually; disable auto-apply to keep overrides when re-recommending.
5. **Validate → Export YAML** — writes `exports/rl_<project>_config.yaml`.

Run PPO training from your own stack using the exported config (see `training/scripts/run_rl_train.py`).

## Export contract

The unified YAML references existing exports:

| Field | File |
|-------|------|
| `env.observations_file` | `sens_<project>_observations.yaml` |
| `env.gains_file` | `ctrl_<project>_gains.yaml` |
| `env.sim_urdf` | `sens_<project>_rl.urdf` |

Your SB3 + ROS2 env loader should:

- Map `task.reward_terms` to shaped scalars each step
- Apply `task.termination` for done/truncation
- Construct `PPO` from `hyperparameters` and `VecEnv` with `parallel.num_envs`
- When `curriculum.enabled` is true, iterate `curriculum.stages` in order: train `timesteps` per stage, check `advance_criteria`, optionally load the previous checkpoint (`load_previous_checkpoint`), then switch `reward_terms` and `command` for the next stage

`custom_params` is exported verbatim for forward-compatible extensions.

## PPO Planner

[PPO Planner](../ppo-planner/) remains available for hyperparameter-only tuning. New projects should use `rl_*_config.yaml` as the canonical trainer contract.

## Tests

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
PYTHONPATH=backend .venv/bin/pytest tests/ -q
```
