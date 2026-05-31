"""Tests for bridge/topic helpers."""
from __future__ import annotations

from bridge_and_topics import (
    analyze_launch_logs,
    bridge_to_parameter_bridge_args,
    load_observations_doc,
    parse_joint_states,
    patch_gz_world_in_topic,
)
from ev_ros_env import sim_env


def test_sim_env_sets_plugin_and_library_paths():
    env = sim_env()
    ros_lib = "/opt/ros/humble/lib"
    assert env["GZ_SIM_SYSTEM_PLUGIN_PATH"].startswith(ros_lib)
    assert ros_lib in env.get("LD_LIBRARY_PATH", "").split(":")


def test_analyze_logs_passes_on_successful_spawn_and_plugin():
    gz_log = "[INFO] [GazeboSimROS2ControlPlugin]: robot_param_node is robot_description"
    spawn_log = "[INFO] [ros_gz_sim]: OK creation of entity."
    errors, warnings = analyze_launch_logs(gz_log, spawn_log, spawn_rc=0)
    assert not errors
    assert not warnings


def test_load_observations_doc():
    text = "# comment\nobservations:\n  imu:\n    topic: /imu\n"
    doc = load_observations_doc(text)
    assert doc["observations"]["imu"]["topic"] == "/imu"


def test_parse_joint_states():
    text = "name:\n- hip\nposition:\n- 0.25\n"
    assert parse_joint_states(text) == {"hip": 0.25}


def test_patch_gz_world_in_topic():
    assert patch_gz_world_in_topic("/world/default/imu", "flat") == "/world/flat/imu"


def test_bridge_to_parameter_bridge_args_patches_world():
    doc = {
        "bridges": [
            {
                "ros_topic": "/imu",
                "gz_topic": "/world/default/imu",
                "ros_type": "sensor_msgs/msg/Imu",
                "gz_type": "gz.msgs.IMU",
                "direction": "GZ_TO_ROS",
            }
        ]
    }
    args = bridge_to_parameter_bridge_args(doc, "flat")
    assert args[0]["gz_topic_name"] == "/world/flat/imu"
