"""Tests for spawn test command builder."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.command_builder import build_spawn_test_stop_command, build_test_spawn_command


def test_build_test_spawn_command_gui():
    cmd = build_test_spawn_command("demo", spawn_z=0.55, headless=False)
    assert "ign gazebo -s" not in cmd
    assert "ign gazebo" in cmd
    assert "DISPLAY=" in cmd


def test_build_test_spawn_command():
    cmd = build_test_spawn_command("demo", spawn_z=0.55)
    assert "ign gazebo -s" in cmd
    assert "ros_gz_sim create" in cmd
    assert "0.55" in cmd


def test_build_spawn_test_stop_command():
    cmd = build_spawn_test_stop_command("demo")
    assert "/spawn/test/stop" in cmd
    assert "demo" in cmd
