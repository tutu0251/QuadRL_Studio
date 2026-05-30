from generator.bridge_args import bridge_to_ros_gz_config, observation_topics


def test_bridge_observation_cross_check():
    bridge = {
        "bridge": [
            {
                "ros_topic_name": "/r/imu",
                "gz_topic_name": "/world/flat/model/r/link/base/sensor/imu/imu",
                "ros_type_name": "sensor_msgs/msg/Imu",
                "gz_type_name": "gz.msgs.IMU",
                "direction": "GZ_TO_ROS",
            }
        ]
    }
    obs = {
        "observations": {
            "imu": {"topic": "/r/imu", "kind": "imu"},
            "missing": {"topic": "/r/none", "kind": "contact"},
        }
    }
    bridge_topics = {e["ros_topic_name"] for e in bridge["bridge"]}
    for topic in observation_topics(obs):
        if topic == "/r/none":
            assert topic not in bridge_topics
        else:
            assert topic in bridge_topics

    cfg = bridge_to_ros_gz_config(bridge)
    assert cfg[0]["ros_topic_name"] == "/clock"
    assert len(cfg) == 2


def test_bridge_to_ros_gz_config_rewrites_default_world():
    bridge = {
        "bridge": [
            {
                "ros_topic_name": "/r/contact",
                "gz_topic_name": "/world/default/model/r/link/foot/sensor/c/contact",
                "ros_type_name": "ros_gz_interfaces/msg/Contacts",
                "gz_type_name": "gz.msgs.Contacts",
                "direction": "GZ_TO_ROS",
            }
        ]
    }
    cfg = bridge_to_ros_gz_config(bridge, "flat")
    assert cfg[1]["gz_topic_name"] == "/world/flat/model/r/link/foot/sensor/c/contact"
