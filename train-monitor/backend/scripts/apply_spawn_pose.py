#!/usr/bin/env python3
"""Apply exported spawn pose via SetEntityPose (used by spawn test)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TRAINING_DIR = REPO_ROOT / "training"
sys.path.insert(0, str(TRAINING_DIR))

import rclpy  # noqa: E402
from quadrl_env.gazebo_reset import _set_entity_pose  # noqa: E402
from rclpy.node import Node  # noqa: E402


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: apply_spawn_pose.py WORLD ENTITY SPAWN_JSON", file=sys.stderr)
        return 2
    world_name = sys.argv[1]
    entity_name = sys.argv[2]
    spawn = json.loads(sys.argv[3])
    rclpy.init()
    node = Node("tm_apply_spawn_pose")
    try:
        _set_entity_pose(
            node,
            world_name=world_name,
            entity_name=entity_name,
            spawn=spawn,
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
