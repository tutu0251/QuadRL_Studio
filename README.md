# QuadRL Studio — Geometry Editor v2

Web-based primitive geometry editor for quadruped robots. Define link/joint structure, edit in 3D with gizmos, validate for ROS2/Gazebo, and export URDF + SDF.

**DEV MODE:** No authentication. Bind `0.0.0.0` for LAN use only.

## Quick start

```bash
cd /home/gazebo/QuadRL_Studio
chmod +x start_*.sh scripts/*.sh
./start_geometry_editor.sh
```

Browser: `http://<ubuntu_ip>:5173`

## Architecture (v2 greenfield)

```
QuadRL_Studio/
├── apps/geometry-editor/     # React + R3F frontend
├── packages/robot-model/     # Shared TypeScript types
├── backend/
│   ├── api/                  # FastAPI routes
│   ├── domain/               # RobotModel + operations
│   ├── templates/            # Starter templates
│   ├── validator/            # ROS2/Gazebo validation
│   ├── exporter/             # URDF + SDF export
│   └── storage/              # Project persistence
└── scripts/smoke_test.sh     # End-to-end API smoke test
```

## Ports

| Service  | Host      | Port |
|----------|-----------|------|
| Backend  | 0.0.0.0   | 8000 |
| Frontend | 0.0.0.0   | 5173 |

## Frontend config

```bash
cp apps/geometry-editor/.env.example apps/geometry-editor/.env
# VITE_API_BASE_URL=http://<ubuntu_ip>:8000
```

## Storage

```
~/quadruped_dev_tool/projects/<project_name>/
  robot_model.json
  snapshots/
  exports/<name>.urdf
  exports/<name>.sdf
```

## UI layout (Unity-style)

- **Left:** Hierarchy panel — expandable robot tree with search, link/joint/shape nodes
- **Center:** 3D Scene view + measure tools strip
- **Right:** Inspector panel — foldout components (Transform, Link, Joint, Shape)
- **Top:** Menu bar (File, Templates, Tools) + viewport toolbar
- **Bottom:** Collapsible Console

## Templates

| Template | Description |
|----------|-------------|
| **12-DOF Quadruped** | 4 legs × 3 revolute joints |
| **8-DOF Quadruped** | Mini dog style |
| **Humanoid (Full Body)** | Pelvis, torso, head, 2 arms, 2 legs |
| **Humanoid Biped** | Torso, head, 2 legs (no arms) |
| MIT Cheetah / Unitree | 16-DOF quadrupeds |
| Parts | Single leg modules, arms, limbs |

Use **Templates** menu → Robots to load a starter shell, then edit in the Inspector and mirror legs in **Tools**.

## Features

- Robot tree editor (hierarchical link → joint → child)
- 3D viewport: primitives, world grid, link/joint frames, joint axes
- Interactive gizmos (translate / rotate / scale) + property forms
- Templates: quadruped, leg modules, MIT Cheetah, Unitree, mini dog
- Leg mirror and copy
- Measurement: distance, height, link length, angle, leg reach
- Validation with export blocking
- Dual export: URDF first, then Gazebo SDF 1.9 via `ign sdf` / `gz sdf` conversion

## API

Docs: `http://<ubuntu_ip>:8000/docs`

Key routes: project CRUD, tree ops, measure, mirror/copy, validate, export URDF/SDF/both, snapshots, WebSocket `/ws/logs`.

## Smoke test

```bash
./scripts/smoke_test.sh
```

## Scope limits (v1)

- Primitives only (box, cylinder, sphere, capsule)
- Visual = collision on export
- Placeholder inertial (mass 1.0)
- No mesh import, Xacro, or physics/ROS2 launch integration
