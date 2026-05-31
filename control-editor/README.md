# Control Editor

Web-based control editor for quadruped robots. Imports `phy_<project>.urdf` from the physics editor, auto-generates position-control metadata (ProfileA), and exports `ros2_control` URDF plus controller YAML for Gazebo Fortress / ROS2 RL.

**DEV MODE:** No authentication. Bind `0.0.0.0` for LAN use only.

## Quick start

```bash
cd /home/gazebo/QuadRL_Studio
chmod +x start_control_editor.sh control-editor/start_*.sh
./start_control_editor.sh
```

Browser: `http://<host>:5175`

## Workflow

1. In **Geometry Editor**, export `geo_<name>.urdf`.
2. In **Physics Editor**, import geo URDF → export `phy_<name>.urdf`.
3. In **Control Editor**, select the project → **Import phy URDF** (auto-generates ProfileA).
4. Review joint Kp/Kd, validate → **Export ros2_control**.

## Ports

| Service  | Port |
|----------|------|
| Backend  | 8002 |
| Frontend | 5175 |

## Storage

```
~/quadruped_dev_tool/projects/<project_name>/
  control_model.json
  exports/phy_<name>.urdf          # physics input
  exports/ctrl_<name>_ros2_control.urdf
  exports/ctrl_<name>_controllers.yaml
  exports/ctrl_<name>_gains.yaml
```

## Gazebo Fortress plugin (gz_ros2_control)

ProfileA exports the official **Gazebo Fortress + ROS 2 Humble** plugin pair:

| Layer | URDF / config value |
|-------|---------------------|
| ros2_control hardware | `gz_ros2_control/GazeboSimSystem` |
| Gazebo system plugin file | `libgz_ros2_control-system.so` |
| Gazebo system plugin class | `gz_ros2_control::GazeboSimROS2ControlPlugin` |
| Controllers | `ctrl_<name>_controllers.yaml` (`joint_trajectory_controller`) |

Do **not** use `ign_ros2_control` or `gazebo_ros2_control` (Classic) on this stack.

### Required ROS packages

```bash
sudo apt install ros-humble-gz-ros2-control ros-humble-ros-gz-sim
```

If Gazebo reports it cannot load the plugin:

```bash
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}
export LD_LIBRARY_PATH=/opt/ros/humble/lib:${LD_LIBRARY_PATH:-}
```

The export-validator sets plugin paths automatically for headless checks.

### Spawn note

[`spawn_gazebo_gui.sh`](../spawn_gazebo_gui.sh) spawns `phy_*.sdf` (physics only, no ros2_control). For controlled simulation, spawn `ctrl_<name>_ros2_control.urdf` with `ros2 run ros_gz_sim create` and load the exported controller YAML (or use a launch file that sets `robot_description` + controller spawner).

### Gazebo export validation

After **Export ros2_control**, the backend runs a headless workspace validation when Gazebo and ROS 2 are installed:

1. Generates a minimal colcon workspace under `workspace_control/`
2. Launches headless Gazebo via `control_readiness.launch.py`
3. Spawns controllers and sends a small joint trajectory probe
4. Confirms `/joint_states` updates and the joint moves

Results appear in the console as **Export validation: passed / skipped / failed**. Skipped means Gazebo or `gz_ros2_control` is not on the machine — export still succeeds.

Manual CLI:

```bash
chmod +x export-validator/scripts/validate_control_runtime.sh
./export-validator/scripts/validate_control_runtime.sh my_robot
```

Or via the control editor script (delegates to export-validator):

```bash
chmod +x control-editor/scripts/validate_gazebo_export.sh
./control-editor/scripts/validate_gazebo_export.sh my_robot
```

API: `POST /api/projects/{name}/validate/export` (async; also runs automatically after export).

## Training profiles

| Profile   | Status        | Description                          |
|-----------|---------------|--------------------------------------|
| ProfileA  | Implemented   | Position control → `joint_trajectory_controller` |
| ProfileB  | Placeholder   | Reserved for future hybrid control   |
| ProfileC  | Placeholder   | Reserved for future torque control   |

## Shared types

`packages/control-model/` — TypeScript types for the control editor frontend.

## API

Docs: `http://<host>:8002/docs`

Key routes: project load/import, profile selection, joint overrides, validate, `POST .../export/ros2_control`, `POST .../validate/gazebo`, `/ws/logs`.
