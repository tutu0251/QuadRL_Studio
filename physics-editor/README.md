# Physics Editor

Web-based physics editor for quadruped robots. Imports `geo_<project>.urdf` from the geometry editor, edits inertials, friction, and joint dynamics, validates for Gazebo Fortress / ROS2 RL, and exports `phy_<project>.urdf` + SDF.

**DEV MODE:** No authentication. Bind `0.0.0.0` for LAN use only.

## Quick start

```bash
cd /home/gazebo/QuadRL_Studio
chmod +x start_physics_editor.sh physics-editor/start_*.sh
./start_physics_editor.sh
```

Browser: `http://<host>:5174`

## Workflow

1. In **Geometry Editor**, export URDF/SDF (`geo_<name>.urdf`).
2. In **Physics Editor**, select the project → **Import geo URDF** (overwrites `physics_model.json`).
3. Edit per-link inertial, friction, joint dynamics in the Inspector.
4. **Validate** → **Export SDF** → spawn in Gazebo:

```bash
./spawn_gazebo_gui.sh --physics my_robot
```

## Ports

| Service  | Port |
|----------|------|
| Backend  | 8001 |
| Frontend | 5174 |

## Storage

```
~/quadruped_dev_tool/projects/<project_name>/
  robot_model.json          # geometry editor
  physics_model.json        # physics editor canonical state
  exports/geo_<name>.urdf   # geometry input
  exports/phy_<name>.urdf   # physics output
  exports/phy_<name>.sdf
```

## Shared types

`packages/robot-model/` — TypeScript types shared with editors (physics-extended `Inertial`, friction, joint dynamics).

## Features

- Import/overwrite from `geo_*.urdf`
- Link inertial: mass, COM, full inertia tensor; auto-estimate from primitives
- Per-link Gazebo friction (μ, μ₂, kp, kd); foot link flag
- Joint dynamics: damping, friction, effort, velocity
- 3D view: read-only geometry, per-link COM, RGB principal inertia arrows, whole-robot COM
- Validation (positive-definite inertia, triangle inequalities, COM bounds, foot friction, placeholder mass)
- URDF + SDF export via `gz sdf` / `ign sdf`

## API

Docs: `http://<host>:8001/docs`

Key routes: project load/import, link inertial/friction, joint dynamics, estimate, validate, export, `/ws/logs`.
