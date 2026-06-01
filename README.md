# QuadRL Studio

Monorepo for robot authoring tools. Each editor lives in its own top-level folder.

| Subproject | Folder | Status |
|------------|--------|--------|
| Geometry Editor | [`geometry-editor/`](geometry-editor/) | v2 — link/joint primitives, URDF/SDF export |
| Physics Editor | [`physics-editor/`](physics-editor/) | v1 — inertials, friction, joint dynamics, phy URDF/SDF |
| Control Editor | [`control-editor/`](control-editor/) | v1 — ProfileA position control, ros2_control export |
| Export Validator | [`export-validator/`](export-validator/) | v1 — workspace-based Gazebo control runtime checks |
| Sensor Editor | [`sensor-editor/`](sensor-editor/) | v1 — IMU/contact/lidar, sens_* RL export |
| Workspace Generator | [`workspace-generator/`](workspace-generator/) | v1 — colcon workspace + RL training readiness validation |
| PPO Planner | [`ppo-planner/`](ppo-planner/) | v1 — PPO hyperparameters + machine-based defaults |
| RL Trainer Editor | [`rl-trainer-editor/`](rl-trainer-editor/) | v1 — rewards, termination, curriculum (PPO settings via PPO Planner) |
| Train Monitor | [`train-monitor/`](train-monitor/) | v1 — start/stop/resume training, checkpoints, TensorBoard, export browser |

## Python environment

One virtual environment at the repo root serves all backends, training, workspace-generator, and export-validator:

```bash
./scripts/ensure_venv.sh
source .venv/bin/activate   # optional for interactive shells
```

`start_*.sh` and `start_all.sh` call this automatically. Per-subproject `*/backend/requirements.txt` files are aggregated by [`requirements.txt`](requirements.txt).

**IDE:** set the Python interpreter to `QuadRL_Studio/.venv/bin/python`.

**Migration:** if you previously used per-folder venvs, remove them to reclaim disk:

```bash
find . -path '*/.venv' -type d -prune
# review the list, then: find . -path '*/.venv' -type d -prune -exec rm -rf {} +
```

## Quick start (Sensor Editor)

```bash
./start_sensor_editor.sh
```

Browser: `http://<ubuntu_ip>:5176` — import `ctrl_<project>_ros2_control.urdf` after exporting from the control editor.

## Quick start (Control Editor)

```bash
./start_control_editor.sh
```

Browser: `http://<ubuntu_ip>:5175` — import `phy_<project>.urdf` after exporting from the physics editor.

## Quick start (Physics Editor)

```bash
./start_physics_editor.sh
```

Browser: `http://<ubuntu_ip>:5174` — import `geo_<project>.urdf` after exporting from the geometry editor.

## Quick start (Geometry Editor)

```bash
cd /home/gazebo/QuadRL_Studio
chmod +x start_geometry_editor.sh geometry-editor/start_*.sh geometry-editor/scripts/*.sh
./start_geometry_editor.sh
```

Browser: `http://<ubuntu_ip>:5173`

## Shared tooling

- [`spawn_gazebo_gui.sh`](spawn_gazebo_gui.sh) — spawn exported SDF in Gazebo Fortress (uses `~/quadruped_dev_tool/projects/`)
- [`fix_git_commit.sh`](fix_git_commit.sh) — fix common git commit blockers (identity, secrets, stale lock)
- [`stop_geometry_editor.sh`](stop_geometry_editor.sh) — stop dev servers before restarting

## Documentation

See [`geometry-editor/README.md`](geometry-editor/README.md) for architecture, API, templates, and smoke tests.

See [`control-editor/README.md`](control-editor/README.md) for the Geometry → Physics → Control pipeline and ros2_control export.

See [`sensor-editor/README.md`](sensor-editor/README.md) for the full four-step pipeline and RL observation YAML.

## Quick start (Workspace Generator)

After exporting from all four editors:

```bash
chmod +x workspace-generator/scripts/*.sh
./workspace-generator/scripts/setup_robot.sh my_robot
```

See [`workspace-generator/README.md`](workspace-generator/README.md) for sensor export validation, build, and runtime readiness checks.

## Quick start (PPO Planner)

```bash
./start_ppo_planner.sh
```

Browser: `http://<ubuntu_ip>:5177` — configure PPO params and export `ppo_<project>_config.yaml` after the sensor pipeline.

See [`ppo-planner/README.md`](ppo-planner/README.md) for machine profiling and recommendation rules.

## Quick start (RL Trainer Editor)

```bash
./start_rl_trainer_editor.sh
```

Browser: `http://<ubuntu_ip>:5178` — configure rewards, thresholds, and PPO settings; export `rl_<project>_config.yaml` after the sensor pipeline.

See [`rl-trainer-editor/README.md`](rl-trainer-editor/README.md) for presets, custom params, and SB3 export contract.

## Quick start (Train Monitor)

After exporting PPO and RL configs:

```bash
./start_train_monitor.sh
```

Browser: `http://<ubuntu_ip>:5179` — start/stop/resume training, browse all editor exports, track checkpoints and runs, view TensorBoard metrics.

See [`train-monitor/README.md`](train-monitor/README.md) for API and training workflow.

## Quick start (PPO training)

After exporting from all editors and generating the workspace:

```bash
./scripts/ensure_venv.sh
.venv/bin/python training/scripts/run_rl_train.py ~/quadruped_dev_tool/projects/<project>
```

Uses `rl_*` + `ppo_*` + sensor/control exports (mock sim by default; `QUADRL_SIM_BACKEND=ros` for Gazebo). See [`training/README.md`](training/README.md).

## Run everything on the training machine

To run **all** editor backends and frontends on the training machine (single command):

```bash
chmod +x start_all.sh
./start_all.sh
```

If you need to override the hostname/IP that the browser should use to reach APIs (defaults to the first `hostname -I` address):

```bash
QUADRL_HOST=<training_machine_ip_or_dns_name> ./start_all.sh
```

(`./start_all_on_training_machine.sh` is an alias for the same script.)
