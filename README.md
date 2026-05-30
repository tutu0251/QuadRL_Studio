# QuadRL Studio

Monorepo for robot authoring tools. Each editor lives in its own top-level folder.

| Subproject | Folder | Status |
|------------|--------|--------|
| Geometry Editor | [`geometry-editor/`](geometry-editor/) | v2 — link/joint primitives, URDF/SDF export |
| Physics Editor | [`physics-editor/`](physics-editor/) | v1 — inertials, friction, joint dynamics, phy URDF/SDF |
| Control Editor | [`control-editor/`](control-editor/) | v1 — ProfileA position control, ros2_control export |
| Sensor Editor | [`sensor-editor/`](sensor-editor/) | v1 — IMU/contact/lidar, sens_* RL export |
| Workspace Generator | [`workspace-generator/`](workspace-generator/) | v1 — colcon workspace + RL training readiness validation |
| PPO Planner | [`ppo-planner/`](ppo-planner/) | v1 — PPO hyperparameters + machine-based defaults |

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
