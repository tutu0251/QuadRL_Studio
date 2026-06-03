# Train Monitor

Runtime dashboard for QuadRL training: start/stop/resume jobs, browse editor exports, track checkpoints and runs, and view TensorBoard metrics.

| Service | Port |
|---------|------|
| Backend API | 8006 |
| Frontend UI | 5179 |

## Quick start

```bash
chmod +x start_train_monitor.sh train-monitor/start_*.sh
./start_train_monitor.sh
```

Browser: `http://<host>:5179`

## Prerequisites

1. Export training configs from **PPO Planner** and **RL Trainer Editor** (`exports/ppo_<name>_config.yaml`, `exports/rl_<name>_config.yaml`).
2. Optional: install Python deps for real SB3 runs (from repo root):

```bash
cd /path/to/QuadRL_Studio && ./scripts/ensure_venv.sh
```

Projects live under `~/quadruped_dev_tool/projects/<name>/` (override with `QUADRL_PROJECTS_DIR`).

## Features

- **Workspace** — generate colcon workspace, build, validate exports, full `setup_robot` pipeline (no shell required)
- **Training control** — start, stop, resume (ROS/Gazebo when workspace + exports are ready)
- **Export browser** — lists all editor export files (geometry, physics, control, sensor, PPO, RL) with YAML/text preview
- **Checkpoints** — scans `checkpoints/*.zip` with size and modified time
- **Runs** — reads `runs/<timestamp>/run_info.yaml` and monitor state
- **Host resources** — realtime CPU, RAM, and GPU utilization on the training machine
- **Metrics** — TensorBoard-style scalar charts from event files; open full TensorBoard in a separate tab via link
- **Training elapsed** — live timer for the current training session
- **Live logs** — WebSocket stream of training subprocess output

## API (selected)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system/stats` | Realtime CPU, RAM, GPU usage |
| GET | `/api/projects` | List projects and training readiness |
| POST | `/api/projects/{name}/load` | Set active project |
| GET | `/api/projects/{name}/exports` | Scan export bundle |
| GET | `/api/projects/{name}/workspace/status` | Workspace / readiness snapshot |
| POST | `/api/projects/{name}/workspace/setup` | Generate + build + validate (full pipeline) |
| POST | `/api/projects/{name}/workspace/generate` | Generate workspace from exports |
| POST | `/api/projects/{name}/workspace/build` | `colcon build` |
| POST | `/api/projects/{name}/workspace/validate-exports` | Sensor/control export alignment |
| POST | `/api/projects/{name}/workspace/validate` | Static / build / runtime readiness |
| POST | `/api/projects/{name}/train/start` | Start training (`dry_run`, `gazebo_headless`, optional `resume_checkpoint`) |
| POST | `/api/projects/{name}/train/stop` | Stop training |
| POST | `/api/projects/{name}/train/resume` | Resume from checkpoint (same body fields as start) |

**Gazebo mode:** `gazebo_headless` defaults to `true` (server-only, no window). Set `false` for GUI to watch the robot in a Gazebo window during training. The backend auto-detects a local X display (e.g. VNC `DISPLAY=:10`) when `DISPLAY` is unset; override with `QUADRL_DISPLAY=:10`. `GET /api/system/display` reports availability.

The Gazebo window opens on the **training host** (VNC/desktop), not inside the browser.

**Stop / exit -9:** Stop sends SIGTERM first (up to `QUADRL_TRAIN_STOP_TIMEOUT_S`, default 30s) so training can run `env.close()` and shut down Gazebo. SIGKILL (`exit code -9`) is only used if the process does not exit in time. Train Monitor always runs `cleanup_gazebo.py` after training exits to stop orphaned Gazebo windows.
| GET | `/api/projects/{name}/checkpoints` | List checkpoints |
| GET | `/api/projects/{name}/runs` | List training runs |
| POST | `/api/projects/{name}/tensorboard/start` | Launch TensorBoard subprocess |
| WS | `/ws/train/logs` | Live training logs + status |

## Architecture

```
Editor exports  →  project/exports/
Train Monitor   →  spawns run_rl_train.py
                 →  reads runs/, checkpoints/
                 →  TensorBoard + scalar parsing
```

Dev mode: no authentication.
