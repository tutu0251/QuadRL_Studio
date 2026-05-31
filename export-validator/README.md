# Export Validator

Headless runtime validation for QuadRL editor exports using colcon workspaces and Gazebo Fortress.

## Control editor validation

Validates `ctrl_*_ros2_control.urdf`, controllers YAML, and gains by:

1. Generating a minimal colcon workspace under `workspace_control/`
2. Building with `colcon build --symlink-install`
3. Launching headless Gazebo via `control_readiness.launch.py`
4. Spawning controllers and sending a small joint trajectory probe
5. Confirming `/joint_states` updates and the joint moves

```bash
chmod +x export-validator/scripts/validate_control_runtime.sh
./export-validator/scripts/validate_control_runtime.sh my_robot
```

Options:

- `--no-build` — skip colcon build when workspace already exists
- `--no-generate` — skip workspace generation (requires existing `workspace_control/`)

Environment:

| Variable | Default |
|----------|---------|
| `QUADRL_PROJECTS_DIR` | `~/quadruped_dev_tool/projects` |

## Sensor editor validation

Validates `sens_*` RL exports by:

1. Generating the full colcon workspace under `workspace/` (requires geometry → physics → control → sensor exports)
2. Building with `colcon build --symlink-install`
3. Launching headless Gazebo via `training_readiness.launch.py` (robot + bridge + controllers)
4. Listing ROS topics and verifying each observation topic from `sens_*_observations.yaml` publishes

```bash
chmod +x export-validator/scripts/validate_sensor_runtime.sh
./export-validator/scripts/validate_sensor_runtime.sh my_robot
```

Options:

- `--no-build` — skip colcon build when workspace already exists
- `--no-generate` — skip workspace generation (requires existing `workspace/`)

The Sensor Editor runs this automatically after **Export RL package** when Gazebo/ROS is installed.

## Integration

The Control Editor Gazebo validation delegates to this module when the runtime stack is installed. Export still succeeds when validation is skipped (Gazebo/ROS not present).

## Tests

```bash
cd export-validator
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r requirements.txt
PYTHONPATH=backend backend/.venv/bin/pytest tests/ -q
```

Exit codes from `validate_control_runtime.sh`: `0` = passed or skipped, `1` = failed.
