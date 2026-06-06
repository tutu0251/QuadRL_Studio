"""Consistent spawn / command / termination heights (base_link world Z)."""
from __future__ import annotations

from dataclasses import dataclass

HEIGHT_REFERENCE = "base_link_origin_z"
FALL_DROP_MARGIN_M = 0.10
PLACEHOLDER_BODY_HEIGHT_M = 0.2933


@dataclass(frozen=True)
class StandingHeightParams:
    spawn_z: float
    target_body_height: float
    fall_base_height_threshold: float
    fall_drop_margin_m: float = FALL_DROP_MARGIN_M


def standing_height_params(
    grounded_spawn_z: float,
    *,
    fall_drop_margin_m: float = FALL_DROP_MARGIN_M,
) -> StandingHeightParams:
    spawn_z = round(float(grounded_spawn_z), 4)
    target = spawn_z
    fall = round(target - float(fall_drop_margin_m), 4)
    return StandingHeightParams(
        spawn_z=spawn_z,
        target_body_height=target,
        fall_base_height_threshold=fall,
        fall_drop_margin_m=float(fall_drop_margin_m),
    )


def fall_threshold_for_target(
    target_body_height: float,
    *,
    fall_drop_margin_m: float = FALL_DROP_MARGIN_M,
) -> float:
    return round(float(target_body_height) - float(fall_drop_margin_m), 4)


def assert_height_policy_consistent(params: StandingHeightParams) -> None:
    if params.target_body_height != params.spawn_z:
        raise ValueError("target_body_height must equal spawn_z")
    if params.fall_base_height_threshold >= params.target_body_height:
        raise ValueError("fall_base_height_threshold must be below target_body_height")
    expected = fall_threshold_for_target(params.target_body_height, fall_drop_margin_m=params.fall_drop_margin_m)
    if params.fall_base_height_threshold != expected:
        raise ValueError(f"fall_base_height_threshold expected {expected}")


def heights_for_target(target_body_height: float) -> StandingHeightParams:
    """Align fall threshold with an existing target (spawn assumed equal to target)."""
    return standing_height_params(target_body_height)
