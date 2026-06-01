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

```bash
cd training
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

For Gazebo training on the robot machine, also source ROS Humble and build the project workspace:

```bash
./workspace-generator/scripts/setup_robot.sh <project>
export QUADRL_SIM_BACKEND=ros
```

## Run

```bash
.venv/bin/python scripts/run_rl_train.py ~/quadruped_dev_tool/projects/<project>
```

Options:

- `--sim-backend auto|mock|ros` — `auto` uses ROS when workspace + rclpy are available
- `--resume checkpoints/ppo_final.zip`
- `--dry-run` — no SB3

Environment variable: `QUADRL_SIM_BACKEND` (same as `--sim-backend`).

## Backends

- **mock** — lightweight integrator; uses exported joint/action/reward/obs contracts. Default for CI and multi-env (`num_envs` > 1).
- **ros** — launches `sim.launch.py`, subscribes to observation topics, publishes `joint_trajectory_controller` goals. Single env only.

Train Monitor (`train-monitor/`) calls this script automatically.

## Tests

```bash
cd training
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
```
