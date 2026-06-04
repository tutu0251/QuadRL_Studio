# Train Monitor

Runtime dashboard for QuadRL training, organized into four monitor subpages. Every action button shows the equivalent bash command (copyable) beneath it.

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

## Subpages

| Tab | Purpose |
|-----|---------|
| **Spawn Monitor** | Confirm default pose from `geo_*_default_pose.yaml`, set spawn offset, configure controller apply delay (`QUADRL_SIM_WARMUP_S`) |
| **Topic Monitor** | Workspace setup/validate, observation topic list, runtime validation status, per-topic confirmation |
| **Training Monitor** | Edit action scales (`ctrl_*_gains.yaml`) and observation scales (`rl_*_config.yaml`), review termination config, filtered training console |
| **Metric Monitor** | Start/stop/resume training, checkpoints, runs/stages, in-app metric charts, TensorBoard, host CPU/RAM/GPU |

Hash routes: `#spawn`, `#topic`, `#training`, `#metric`

## Prerequisites

1. Export training configs from **PPO Planner** and **RL Trainer Editor** (`exports/ppo_<name>_config.yaml`, `exports/rl_<name>_config.yaml`).
2. Optional: install Python deps for real SB3 runs (from repo root):

```bash
cd /path/to/QuadRL_Studio && ./scripts/ensure_venv.sh
```

Projects live under `~/quadruped_dev_tool/projects/<name>/` (override with `QUADRL_PROJECTS_DIR`).

## Bash command previews

- `GET /api/projects/{name}/commands/preview?action=…&params=…` — shell equivalent for UI actions
- Mutating endpoints also return a `command` field in the JSON response
- Implemented in `backend/api/command_builder.py`; UI component `frontend/src/components/CommandPreview.tsx`

## API (selected)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system/stats` | Realtime CPU, RAM, GPU usage |
| GET | `/api/projects` | List projects and training readiness |
| POST | `/api/projects/{name}/load` | Set active project |
| GET | `/api/projects/{name}/commands/preview` | Bash command preview for an action |
| GET | `/api/projects/{name}/spawn-config` | Default pose, offset, controller delay |
| PATCH | `/api/projects/{name}/spawn-config` | Update spawn offset / timing / pose confirmed |
| GET | `/api/projects/{name}/topics` | Observation topics + validation status |
| PATCH | `/api/projects/{name}/topics/confirmations` | Persist confirmed topic list |
| GET | `/api/projects/{name}/training-config` | Action/obs scales and termination summary |
| PATCH | `/api/projects/{name}/training-config` | Write scales back to export YAML |
| GET | `/api/projects/{name}/exports` | Scan export bundle |
| GET | `/api/projects/{name}/workspace/status` | Workspace / readiness snapshot |
| POST | `/api/projects/{name}/workspace/setup` | Generate + build + validate (full pipeline) |
| POST | `/api/projects/{name}/train/start` | Start training |
| POST | `/api/projects/{name}/train/stop` | Stop training |
| POST | `/api/projects/{name}/train/resume` | Resume from checkpoint |
| POST | `/api/projects/{name}/tensorboard/start` | Launch TensorBoard subprocess |
| WS | `/ws/train/logs` | Live training logs + status |

**Gazebo mode:** `gazebo_headless` defaults to `true`. Set `false` for GUI. `GET /api/system/display` reports availability.

**Controller warmup:** Spawn Monitor saves `controller_apply_delay_s` (delay after spawn before control applies). Test spawn waits this long after a successful spawn; training passes it as `QUADRL_SIM_WARMUP_S`.

## Architecture

```
Editor exports  →  project/exports/
Train Monitor   →  spawns run_rl_train.py
                 →  reads runs/, checkpoints/
                 →  TensorBoard + scalar parsing
                 →  four subpages + command previews
```

Dev mode: no authentication.
