"""Baking must keep a root link's origin on its own geometry (the trunk).

Regression for the confusing negative spawn_z: the editor authors base_link's
frame at the standing height, but baking used to fold that position into the
trunk shape, re-rooting base_link's origin to the model origin (~0.3 m below the
trunk) and producing a negative grounded spawn_z. A root link has no parent joint
to carry its placement, so its frame position is the spawn reference and must not
be baked into its own shapes. Non-root link frames must still bake fully.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import Frame, Joint, JointType, Link, PrimitiveShape, PrimitiveType, RobotModel, Vec3
from domain.pose_utils import compute_grounded_spawn_z_for_model, ensure_default_pose
from domain.transform_bake import _is_identity_frame, bake_link_frames


def _root_at_standing_height() -> RobotModel:
    base = Link(name="base_link", shapes=[PrimitiveShape(type=PrimitiveType.BOX, dimensions=[0.4, 0.2, 0.08])])
    base.frame = Frame(position=Vec3(z=0.30))  # editor places the root at standing height
    foot = Link(name="foot", shapes=[PrimitiveShape(type=PrimitiveType.SPHERE, dimensions=[0.02])])
    leg = Joint(
        name="leg",
        type=JointType.FIXED,
        parentLinkId=base.id,
        childLinkId=foot.id,
        originPosition=Vec3(z=-0.25),  # foot 0.25 below the trunk centre
    )
    foot.parentJointId = leg.id
    return RobotModel(name="bot", links=[base, foot], joints=[leg])


def test_root_frame_position_keeps_origin_on_trunk():
    m = _root_at_standing_height()
    ensure_default_pose(m)

    # Grounded spawn_z is the POSITIVE trunk-centre standing height (foot bottom at
    # -0.27 -> spawn_z = +0.27), not a negative model-origin value.
    assert compute_grounded_spawn_z_for_model(m) == pytest.approx(0.27, abs=1e-3)

    baked = bake_link_frames(copy.deepcopy(m))
    bl = next(l for l in baked.links if l.name == "base_link")
    assert _is_identity_frame(bl.frame)
    # The trunk shape stays centred on the origin — NOT shoved up by the 0.30 frame.
    assert bl.shapes[0].localPosition.z == pytest.approx(0.0, abs=1e-9)
    # The leg offset is untouched (origin moved to the trunk, not the legs).
    leg = baked.joints[0]
    assert leg.originPosition.z == pytest.approx(-0.25, abs=1e-9)


def test_non_root_link_frame_still_bakes():
    base = Link(name="base_link", shapes=[PrimitiveShape(type=PrimitiveType.BOX, dimensions=[0.2, 0.2, 0.05])])
    child = Link(name="child", shapes=[PrimitiveShape(type=PrimitiveType.BOX, dimensions=[0.1, 0.1, 0.1])])
    child.frame = Frame(position=Vec3(z=0.07))  # internal offset; must fold into geometry
    j = Joint(name="j", type=JointType.FIXED, parentLinkId=base.id, childLinkId=child.id)
    child.parentJointId = j.id
    m = RobotModel(name="b", links=[base, child], joints=[j])

    baked = bake_link_frames(copy.deepcopy(m))
    cb = next(l for l in baked.links if l.name == "child")
    assert _is_identity_frame(cb.frame)
    assert cb.shapes[0].localPosition.z == pytest.approx(0.07, abs=1e-9)
