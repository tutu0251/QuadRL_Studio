# QuadRL Studio

Monorepo for robot authoring tools. Each editor lives in its own top-level folder.

| Subproject | Folder | Status |
|------------|--------|--------|
| Geometry Editor | [`geometry-editor/`](geometry-editor/) | v2 — link/joint primitives, URDF/SDF export |
| Physics Editor | `physics-editor/` | planned |

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
