"""Tests for base spawn + offset loading on ProjectArtifacts."""
from __future__ import annotations

from pathlib import Path

import yaml

from quadrl_env.project_config import load_project_artifacts


def test_loads_base_spawn_and_offset(tmp_path: Path) -> None:
    project = tmp_path / "robot_a"
    exports = project / "exports"
    exports.mkdir(parents=True)
    name = "robot_a"
    (exports / f"rl_{name}_config.yaml").write_text(
        "env:\n  observations_file: sens_robot_a_observations.yaml\n"
        "  gains_file: ctrl_robot_a_gains.yaml\n",
        encoding="utf-8",
    )
    (exports / f"sens_{name}_observations.yaml").write_text("observations: {}\n", encoding="utf-8")
    (exports / f"ctrl_{name}_gains.yaml").write_text("joints: {}\n", encoding="utf-8")
    (exports / f"geo_{name}_default_pose.yaml").write_text(
        yaml.dump(
            {
                "_base_spawn": {"x": 1.0, "y": 0.0, "z": 0.4, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                "spawn_offset": {"dx": 0.1, "dy": 0.0, "dz": 0.0, "droll": 0.0, "dpitch": 0.0, "dyaw": 0.0},
                "spawn": {"x": 1.1, "y": 0.0, "z": 0.4, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            }
        ),
        encoding="utf-8",
    )

    artifacts = load_project_artifacts(project)
    assert artifacts.base_spawn["x"] == 1.0
    assert artifacts.spawn_offset.dx == 0.1
    assert artifacts.spawn_config["x"] == 1.1
