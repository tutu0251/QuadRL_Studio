# Sensor Editor

Web-based sensor editor for quadruped robots. Imports `ctrl_<project>_ros2_control.urdf` from the control editor, configures IMU / contact / lidar sensors, and exports an RL training package for Gazebo Fortress and a custom ROS2 stack.

**DEV MODE:** No authentication. Bind `0.0.0.0` for LAN use only.

## Quick start

```bash
cd /home/gazebo/QuadRL_Studio
chmod +x start_sensor_editor.sh sensor-editor/start_*.sh
./start_sensor_editor.sh
```

Browser: `http://<host>:5176`

## Workflow

1. **Geometry Editor** → `geo_<name>.urdf`
2. **Physics Editor** → `phy_<name>.urdf`
3. **Control Editor** → `ctrl_<name>_ros2_control.urdf` (+ controllers/gains YAML)
4. **Sensor Editor** → select project → **Import ctrl URDF** → add sensors → **Export RL package**

Optional: **Bootstrap quadruped sensors** (File menu) adds base IMU + foot contacts from `control_model.json` child links.

## Ports

| Service  | Port |
|----------|------|
| Backend  | 8003 |
| Frontend | 5176 |

## Storage

```
~/quadruped_dev_tool/projects/<project_name>/
  sensor_model.json
  exports/ctrl_<name>_ros2_control.urdf   # input (unchanged)
  exports/sens_<name>_rl.urdf
  exports/sens_<name>.sdf
  exports/sens_<name>_bridge.yaml
  exports/sens_<name>_observations.yaml
```

## Shared types

`packages/sensor-model/` — TypeScript types for the frontend.

## Loading observations in your ROS2 env

```python
import yaml

with open("sens_my_robot_observations.yaml") as f:
    spec = yaml.safe_load(f)

for key, obs in spec["observations"].items():
    topic = obs["topic"]
    msg_type = obs["msg_type"]
    # subscribe in your training node
```

Run `ros2 run ros_gz_bridge parameter_bridge` with the generated `sens_*_bridge.yaml` mappings (adjust `gz_topic_name` after first spawn if world/model paths differ).

## API

Docs: `http://<host>:8003/docs`

Key routes: load/import ctrl, sensor CRUD, validate, `POST .../export/rl`, `/ws/logs`.
