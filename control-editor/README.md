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

Key routes: project load/import, profile selection, joint overrides, validate, `POST .../export/ros2_control`, `/ws/logs`.
