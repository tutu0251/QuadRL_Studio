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
