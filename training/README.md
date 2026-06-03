# QuadRL Training

PPO training launcher that loads **all QuadRL editor exports** for quadruped locomotion:

| Export | Used for |
|--------|----------|
| `rl_<project>_config.yaml` | Observations, rewards, termination, curriculum, commands |
| `ppo_<project>_config.yaml` | Hyperparameters, parallel envs, checkpoints |
| `sens_<project>_observations.yaml` | Sensor topics, fields, bridge contract |
| `ctrl_<project>_controllers.yaml` | Joint names, JTC action targets |
| `ctrl_<project>_gains.yaml` | `action_scale`, default positions, PD metadata |
| `workspace/` (built) | ROS 2 + Gazebo simulation |

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

- `--sim-backend auto|ros` — `auto` requires a built workspace and rclpy
- `--resume checkpoints/ppo_final.zip`
- `--dry-run` — no SB3

Environment variable: `QUADRL_SIM_BACKEND` (same as `--sim-backend`).

## Simulation

Training uses **ROS 2 + Gazebo** only: launches `sim.launch.py`, subscribes to observation topics, and publishes `joint_trajectory_controller` goals. Only one parallel env is supported (`num_envs` > 1 is clamped to 1).

Train Monitor (`train-monitor/`) calls this script automatically.

## Tests

```bash
./scripts/ensure_venv.sh
PYTHONPATH=training .venv/bin/python -m pytest training/tests/ -q
```

End-to-end training smoke test (requires built workspace + Gazebo):

```bash
QUADRL_INTEGRATION=1 PYTHONPATH=training .venv/bin/python -m pytest training/tests/test_tensorboard_smoke.py -q
```
