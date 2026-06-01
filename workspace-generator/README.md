# QuadRL Workspace Generator

Generate a per-project ROS 2 colcon workspace from QuadRL Studio exports, build it, and validate full training readiness (sim + controllers + bridge + observation topics).

## Prerequisites

Complete the four-editor pipeline for your robot:

1. Geometry → `geo_<name>.urdf`
2. Physics → `phy_<name>.urdf`
3. Control → `ctrl_<name>_ros2_control.urdf` (+ controllers/gains YAML)
4. Sensor → `sens_<name>_rl.urdf` (+ bridge + observations YAML)

System packages (ROS 2 Humble + Gazebo Fortress):

```bash
sudo apt install ros-humble-gz-ros2-control ros-humble-ros-gz-sim \
  ros-humble-ros-gz-bridge ros-humble-controller-manager \
  ros-humble-joint-state-broadcaster ros-humble-joint-trajectory-controller \
  python3-colcon-common-extensions
```

## Quick start

```bash
cd /home/gazebo/QuadRL_Studio
chmod +x workspace-generator/scripts/*.sh
./workspace-generator/scripts/setup_robot.sh my_robot
```

This generates `~/quadruped_dev_tool/projects/my_robot/workspace/`, runs `colcon build`, and performs full-stack validation.

## Individual commands

```bash
./workspace-generator/scripts/validate_sensor_exports.sh my_robot   # sensor exports only
./workspace-generator/scripts/generate_workspace.sh my_robot
./workspace-generator/scripts/build_workspace.sh my_robot
./workspace-generator/scripts/validate_training_readiness.sh my_robot
```

Partial validation:

```bash
./workspace-generator/scripts/validate_training_readiness.sh my_robot --static-only
./workspace-generator/scripts/validate_training_readiness.sh my_robot --skip-runtime
```

## Generated workspace

```
~/quadruped_dev_tool/projects/<name>/workspace/
  src/<name>_description/   # URDF + configs
  src/<name>_bringup/       # launch + flat.world
  workspace_manifest.json
  readiness_report.json
```

Launch interactive sim after build:

```bash
source ~/quadruped_dev_tool/projects/my_robot/workspace/install/setup.bash
ros2 launch my_robot_bringup sim.launch.py
```

## Validation phases

| Phase | Checks |
|-------|--------|
| Sensor exports | URDF sensors + gz_ros2_control plugin; bridge ↔ observations alignment; control YAML refs; message types |
| Static | All pipeline exports present; controller joints in URDF; workspace hash drift |
| Build | `colcon build --symlink-install` succeeds |
| Runtime | Headless sim; active controllers; every observation topic publishes at least one message |

Exit codes: `0` = ready, `1` = failed, `2` = runtime skipped (ROS/Gazebo not installed).

If runtime validation fails with FastDDS shared-memory errors, stop stale sim processes and clear locks:

```bash
pkill -f training_readiness.launch.py
pkill -f "ign gazebo"
rm -f /dev/shm/fastrtps*
```

## Environment

| Variable | Default |
|----------|---------|
| `QUADRL_PROJECTS_DIR` | `~/quadruped_dev_tool/projects` |

## Tests

```bash
./scripts/ensure_venv.sh
PYTHONPATH=workspace-generator/backend .venv/bin/python -m pytest workspace-generator/tests/ -q
```
