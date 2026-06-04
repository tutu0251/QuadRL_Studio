"""Robot templates must export a consistent height_policy."""
from __future__ import annotations

import pytest

from domain.models import RobotModel
from domain.pose_utils import export_default_pose_yaml
from domain.standing_heights import assert_height_policy_consistent
from templates.registry import TEMPLATE_BUILDERS, TEMPLATE_META, insert_template


@pytest.mark.parametrize(
    "template_id",
    [tid for tid, meta in TEMPLATE_META.items() if meta.get("category") == "robot"],
)
def test_robot_template_export_height_policy(template_id: str) -> None:
    model = RobotModel(name=f"test_{template_id}")
    insert_template(model, template_id)
    doc = export_default_pose_yaml(model)
    policy = doc.get("height_policy") or {}
    spawn_z = float(doc["spawn"]["z"])
    target = float(policy.get("target_body_height", spawn_z))
    fall = float(policy.get("fall_base_height_threshold", spawn_z - 0.1))
    from domain.standing_heights import StandingHeightParams

    params = StandingHeightParams(
        spawn_z=spawn_z,
        target_body_height=target,
        fall_base_height_threshold=fall,
    )
    assert_height_policy_consistent(params)
    assert policy.get("reference") == "base_link_origin_z"
