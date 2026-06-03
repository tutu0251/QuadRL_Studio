#!/usr/bin/env python3
"""CLI: stop Gazebo processes started by RL training (called from Train Monitor on exit)."""
from __future__ import annotations

import sys
from pathlib import Path

_TRAINING = Path(__file__).resolve().parents[1]
if str(_TRAINING) not in sys.path:
    sys.path.insert(0, str(_TRAINING))

from quadrl_env.ros_sim import shutdown_shared_gazebo  # noqa: E402


def main() -> int:
    shutdown_shared_gazebo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
