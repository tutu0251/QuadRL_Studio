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

Training uses **ROS 2 + Gazebo** only: launches `sim.launch.py`, subscribes to observation topics, and publishes `joint_trajectory_controller` goals.

**Parallel envs.** `parallel.num_envs > 1` runs that many envs concurrently via SB3 `SubprocVecEnv` — one Gazebo instance per env, each isolated on **two** transport layers: its own `ROS_DOMAIN_ID` (`base..base+num_envs`, eval at `base+num_envs`) for the ROS 2 / DDS graph, and its own `IGN_PARTITION`/`GZ_PARTITION` (`quadrl_<domain>`) for Gazebo's own ign-transport graph. Both are required: `ROS_DOMAIN_ID` does not reach gz-transport, so without a partition the `ros_gz` bridges would cross-wire one env's Gazebo topics into another's ROS state. Each parallel env also gets its own ign-common log dir (`IGN_LOG_PATH`/`GZ_LOG_PATH` → `<project>/gazebo_logs/quadrl_<domain>`) so concurrent servers don't write into the shared `~/.ignition`. `vec_env_type` is forced to `subproc` when `num_envs > 1` (a single-process `dummy` vec env cannot isolate per-env ROS graphs). `num_envs = 1` keeps the original single shared-Gazebo path unchanged. Expect roughly `num_envs ×` the RAM/CPU of one sim, so size `num_envs` to the host (the PPO Planner's parallel guard recommends a ceiling). Under a curriculum, sims are restarted per stage rather than reused.

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
