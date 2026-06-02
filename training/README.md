# QuadRL Training

PPO training launcher that loads **all QuadRL editor exports** for quadruped locomotion:

| Export | Used for |
|--------|----------|
| `rl_<project>_config.yaml` | Observations, rewards, termination, curriculum, commands |
| `ppo_<project>_config.yaml` | Hyperparameters, parallel envs, checkpoints |
| `sens_<project>_observations.yaml` | Sensor topics, fields, bridge contract |
| `ctrl_<project>_controllers.yaml` | Joint names, JTC action targets |
| `ctrl_<project>_gains.yaml` | `action_scale`, default positions, PD metadata |
| `workspace/` (built) | ROS 2 + Gazebo sim when using `ros` backend |

## Install

From the repo root (see also root [`README.md`](../README.md#python-environment)):

```bash
./scripts/ensure_venv.sh
```

For Gazebo training on the robot machine, build the project workspace (ROS Humble must be installed):

```bash
./workspace-generator/scripts/setup_robot.sh <project>
export QUADRL_SIM_BACKEND=ros
```

The training launcher re-execs under `source /opt/ros/humble/setup.bash` so **rclpy** works from the repo `.venv` / `training/.venv` (you do not need to source ROS manually when using Train Monitor or `run_rl_train.py`).

## Run

```bash
.venv/bin/python training/scripts/run_rl_train.py ~/quadruped_dev_tool/projects/<project>
```

Options:

- `--sim-backend auto|mock|ros` — `auto` uses ROS when workspace + rclpy are available
- `--resume checkpoints/ppo_final.zip`
- `--dry-run` — no SB3

Environment variable: `QUADRL_SIM_BACKEND` (same as `--sim-backend`).

## Backends

- **mock** — lightweight integrator; uses exported joint/action/reward/obs contracts. Default for CI and multi-env (`num_envs` > 1).
- **ros** — launches `sim.launch.py` (headless by default), subscribes to observation topics, publishes `joint_trajectory_controller` goals. Single env only.

Environment variables:

- `QUADRL_SIM_BACKEND` — `auto`, `mock`, or `ros`
- `QUADRL_GZ_HEADLESS` — `true` (default) for server-only Gazebo; set `false` for GUI debugging

Train Monitor exposes **Headless Gazebo** on the Training panel (maps to `--gazebo-headless` / `--no-gazebo-headless`).

Train Monitor (`train-monitor/`) calls this script automatically.

## Tests

```bash
./scripts/ensure_venv.sh
PYTHONPATH=training .venv/bin/python -m pytest training/tests/ -q
```
