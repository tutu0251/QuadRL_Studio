"""Tests for spawn height recalculation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.spawn_height_sync import recalculate_spawn_and_training_heights


def test_recalculate_spawn_and_training_heights(tmp_path: Path, monkeypatch) -> None:
    name = "bot_sync"
    project = tmp_path / name
    exports = project / "exports"
    exports.mkdir(parents=True)

    urdf = exports / f"geo_{name}.urdf"
    urdf.write_text(
        """<?xml version="1.0"?>
<robot name="bot">
  <link name="base"/>
  <link name="foot">
    <collision>
      <origin xyz="0 0 0"/>
      <geometry><sphere radius="0.02"/></geometry>
    </collision>
  </link>
  <joint name="knee" type="fixed">
    <parent link="base"/>
    <child link="foot"/>
    <origin xyz="0 0 -0.4"/>
  </joint>
</robot>
""",
        encoding="utf-8",
    )

    (exports / f"geo_{name}_default_pose.yaml").write_text(
        yaml.dump(
            {
                "name": "Default Stand",
                "spawn": {"x": 0, "y": 0, "z": 0.5, "roll": 0, "pitch": 0, "yaw": 0},
                "joints": {"knee": 0.0},
            }
        ),
        encoding="utf-8",
    )
    (exports / f"rl_{name}_config.yaml").write_text(
        "task:\n  command:\n    target_body_height: 0.35\n"
        "  termination:\n    fall_base_height_threshold: 0.12\n",
        encoding="utf-8",
    )

    import storage.project_storage as ps

    monkeypatch.setattr(ps, "PROJECTS_ROOT", tmp_path)

    result = recalculate_spawn_and_training_heights(name)
    assert result["spawn_z"] == pytest.approx(0.42, abs=1e-3)
    assert result["target_body_height"] == pytest.approx(0.42, abs=1e-3)
    assert result["fall_base_height_threshold"] == pytest.approx(0.32, abs=1e-3)
    assert result["fall_base_height_threshold"] < result["target_body_height"]

    pose_doc = yaml.safe_load((exports / f"geo_{name}_default_pose.yaml").read_text())
    assert pose_doc["spawn"]["z"] == pytest.approx(0.42, abs=1e-3)
    assert pose_doc["height_policy"]["fall_base_height_threshold"] == pytest.approx(0.32, abs=1e-3)

    rl_doc = yaml.safe_load((exports / f"rl_{name}_config.yaml").read_text())
    assert rl_doc["task"]["command"]["target_body_height"] == pytest.approx(0.42, abs=1e-3)
    assert rl_doc["task"]["termination"]["fall_base_height_threshold"] == pytest.approx(0.32, abs=1e-2)
