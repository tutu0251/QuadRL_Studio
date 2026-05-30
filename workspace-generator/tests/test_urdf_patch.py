from generator.urdf_patch import (
    gazebo_effective_link,
    patch_bridge_world,
    patch_bridge_yaml,
    patch_contact_sensors,
    patch_controllers_parameters,
)


def test_patch_bridge_fixed_joint_links():
    urdf = """<?xml version='1.0'?>
<robot name="t">
  <joint name="ankle" type="fixed">
    <parent link="calf"/>
    <child link="foot"/>
  </joint>
</robot>"""
    bridge = """bridge:
- ros_topic_name: /t/foot_imu
  gz_topic_name: /world/empty/model/t/link/foot/sensor/foot_imu/imu
  parent_link: foot
"""
    out = patch_bridge_yaml(bridge, urdf, "flat")
    assert "/link/calf/sensor/foot_imu/imu" in out
    assert "/link/foot/sensor/foot_imu/imu" not in out


def test_gazebo_effective_link_chain():
    fixed = {"foot": "calf", "calf": "thigh"}
    assert gazebo_effective_link("foot", fixed) == "thigh"


def test_patch_controllers_parameters_basename():
    urdf = """<?xml version='1.0'?>
<robot name="t">
  <gazebo>
    <plugin filename="libgz_ros2_control-system.so" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
      <parameters>/abs/path/ctrl_bot_controllers.yaml</parameters>
    </plugin>
  </gazebo>
</robot>"""
    out = patch_controllers_parameters(urdf, "ctrl_bot_controllers.yaml")
    assert "<parameters>ctrl_bot_controllers.yaml</parameters>" in out
    assert "/abs/path" not in out


def test_patch_contact_sensor_collision_after_fixed_joint():
    urdf = """<?xml version='1.0'?>
<robot name="t">
  <link name="calf">
    <collision/>
  </link>
  <link name="foot">
    <collision/>
  </link>
  <joint name="ankle" type="fixed">
    <parent link="calf"/>
    <child link="foot"/>
  </joint>
  <gazebo reference="foot">
    <sensor name="foot_contact" type="contact">
      <contact><collision>collision</collision></contact>
    </sensor>
  </gazebo>
</robot>"""
    out = patch_contact_sensors(urdf)
    assert "foot_collision" in out
    assert out.count("foot_contact") == 1
    assert "<collision>collision</collision>" not in out


def test_patch_bridge_world():
    text = "gz_topic_name: /world/empty/model/x"
    out = patch_bridge_world(text, "flat")
    assert "/world/flat/model/x" in out


def test_patch_bridge_world_default_placeholder():
    text = "gz_topic_name: /world/default/model/x/link/base/sensor/imu/imu"
    out = patch_bridge_world(text, "flat")
    assert "/world/flat/model/x" in out
    assert "/world/default/" not in out
