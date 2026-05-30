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
<<<<<<< Updated upstream
=======
  <gazebo reference="ankle"><preserveFixedJoint>true</preserveFixedJoint></gazebo>
</robot>"""
    bridge = """bridge:
- ros_topic_name: /t/foot_imu
  gz_topic_name: /world/empty/model/t/link/foot/sensor/foot_imu/imu
  parent_link: foot
"""
    out = patch_bridge_yaml(bridge, urdf, "flat")
    assert "/link/foot/sensor/foot_imu/imu" in out
    assert "/link/calf/sensor/foot_imu/imu" not in out


def test_patch_bridge_removes_lumped_foot_when_not_preserved():
    urdf = """<?xml version='1.0'?>
<robot name="t">
  <joint name="ankle" type="fixed">
    <parent link="calf"/>
    <child link="foot"/>
  </joint>
>>>>>>> Stashed changes
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


<<<<<<< Updated upstream
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
=======
def test_patch_contact_sensor_foot_link():
    urdf = """<?xml version='1.0'?>
<robot name="t">
  <link name="rr_calf_link">
    <collision name="rr_calf_link_collision"/>
  </link>
  <link name="rr_foot_link">
    <collision/>
  </link>
  <joint name="rr_ankle_fixed" type="fixed">
    <parent link="rr_calf_link"/>
    <child link="rr_foot_link"/>
  </joint>
  <gazebo reference="rr_foot_link">
    <sensor name="rr_foot_link_contact" type="contact">
      <contact><collision>collision</collision></contact>
    </sensor>
  </gazebo>
</robot>"""
    out = patch_contact_sensors(urdf)
    assert "<preserveFixedJoint>true</preserveFixedJoint>" in out
    assert 'reference="rr_ankle_fixed"' in out
    assert "<collision>rr_foot_link_collision</collision>" in out
    assert "fixed_joint_lump" not in out
    assert out.count("rr_foot_link_contact") == 1
    assert 'reference="rr_foot_link"' in out


def test_patch_contact_sensor_collision_non_foot():
    urdf = """<?xml version='1.0'?>
<robot name="t">
  <link name="base_link">
    <collision/>
  </link>
  <gazebo reference="base_link">
    <sensor name="base_contact" type="contact">
>>>>>>> Stashed changes
      <contact><collision>collision</collision></contact>
    </sensor>
  </gazebo>
</robot>"""
    out = patch_contact_sensors(urdf)
<<<<<<< Updated upstream
    assert "foot_collision" in out
    assert out.count("foot_contact") == 1
=======
    assert "base_link_collision" in out
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======


def test_foot_contact_sdf_avoids_fixed_joint_lump_names():
    import re
    import subprocess
    import tempfile
    from pathlib import Path

    urdf = """<?xml version='1.0'?>
<robot name="t">
  <link name="rr_calf_link">
    <inertial><mass value="1"/><inertia ixx="0.01" ixy="0" ixz="0" iyy="0.01" iyz="0" izz="0.01"/></inertial>
    <collision name="rr_calf_link_collision"><geometry><box size="0.1 0.1 0.1"/></geometry></collision>
  </link>
  <link name="rr_foot_link">
    <inertial><mass value="0.1"/><inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.001"/></inertial>
    <collision><geometry><sphere radius="0.02"/></geometry></collision>
  </link>
  <joint name="rr_ankle_fixed" type="fixed">
    <parent link="rr_calf_link"/>
    <child link="rr_foot_link"/>
  </joint>
  <gazebo reference="rr_foot_link">
    <sensor name="rr_foot_link_contact" type="contact">
      <contact><collision>collision</collision></contact>
    </sensor>
  </gazebo>
</robot>"""
    patched = patch_contact_sensors(urdf)
    path = Path(tempfile.mkdtemp()) / "robot.urdf"
    path.write_text(patched)
    proc = subprocess.run(["ign", "sdf", "-p", str(path)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    sdf = proc.stdout
    assert "fixed_joint_lump" not in sdf
    assert re.search(r"<link name='rr_foot_link'>", sdf)
    assert "rr_foot_link_collision" in sdf
    contact_ref = re.search(r"<contact>\s*<collision>([^<]+)</collision>", sdf)
    assert contact_ref and contact_ref.group(1) == "rr_foot_link_collision"
>>>>>>> Stashed changes
