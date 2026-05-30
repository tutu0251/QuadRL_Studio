from paths import ProjectPaths
from validator.sensor_export_validator import validate_sensor_exports


def _write_minimal_exports(paths: ProjectPaths) -> None:
    paths.exports_dir.mkdir(parents=True)
    paths.controllers_yaml().write_text(
        "joint_trajectory_controller:\n  ros__parameters:\n    joints: [j1]\n",
        encoding="utf-8",
    )
    paths.gains_yaml().write_text("j1:\n  kp: 1.0\n  kd: 0.1\n", encoding="utf-8")
    paths.sens_rl_urdf().write_text(
        """<?xml version='1.0'?>
<robot name="bot">
  <link name="base"/>
  <joint name="j1" type="revolute"><parent link="base"/><child link="base"/></joint>
  <gazebo>
    <plugin filename="libgz_ros2_control-system.so" name="gz_ros2_control::GazeboSimROS2ControlPlugin"/>
  </gazebo>
  <gazebo reference="base">
    <sensor name="imu" type="imu"/>
  </gazebo>
</robot>""",
        encoding="utf-8",
    )
    paths.bridge_yaml().write_text(
        """bridge:
- ros_topic_name: /bot/imu
  gz_topic_name: /world/default/model/bot/link/base/sensor/imu/imu
  ros_type_name: sensor_msgs/msg/Imu
  gz_type_name: gz.msgs.IMU
  direction: GZ_TO_ROS
  sensor_name: imu
  parent_link: base
""",
        encoding="utf-8",
    )
    paths.observations_yaml().write_text(
        """robot_name: bot
sim_urdf: sens_bot_rl.urdf
topic_prefix: /bot
gz_model_name: bot
control:
  controllers_yaml: ctrl_bot_controllers.yaml
  gains_yaml: ctrl_bot_gains.yaml
observations:
  imu:
    kind: imu
    topic: /bot/imu
    msg_type: sensor_msgs/Imu
    rate_hz: 100
    parent_link: base
    fields: [angular_velocity]
""",
        encoding="utf-8",
    )


def test_sensor_exports_valid(tmp_path):
    paths = ProjectPaths("bot", tmp_path)
    _write_minimal_exports(paths)
    result = validate_sensor_exports(paths)
    assert result["valid"], result["errors"]


def test_sensor_exports_fails_on_bridge_observation_mismatch(tmp_path):
    paths = ProjectPaths("bot", tmp_path)
    _write_minimal_exports(paths)
    paths.observations_yaml().write_text(
        paths.observations_yaml().read_text().replace("/bot/imu", "/bot/missing"),
        encoding="utf-8",
    )
    result = validate_sensor_exports(paths)
    assert not result["valid"]
    assert any("not in bridge" in e for e in result["errors"])


def test_sensor_exports_valid_for_my_robot():
    paths = ProjectPaths("my_robot")
    if not paths.bridge_yaml().is_file():
        return
    result = validate_sensor_exports(paths)
    assert result["valid"], result["errors"]
