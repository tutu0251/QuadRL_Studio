"""Consistent spawn / command / termination heights (base_link world Z)."""
from __future__ import annotations

from dataclasses import dataclass

# Same frame as Gazebo spawn and nav_msgs/Odometry pose.position.z on base_link.
HEIGHT_REFERENCE = "base_link_origin_z"

# Allowed drop below nominal stand before fall termination (m).
FALL_DROP_MARGIN_M = 0.10


@dataclass(frozen=True)
class StandingHeightParams:
    """Heights for grounded default stand (feet on z=0)."""

    spawn_z: float
    target_body_height: float
    fall_base_height_threshold: float
    fall_drop_margin_m: float = FALL_DROP_MARGIN_M

    def as_metadata(self) -> dict[str, float | str]:
        return {
            "reference": HEIGHT_REFERENCE,
            "spawn_z": self.spawn_z,
            "target_body_height": self.target_body_height,
            "fall_base_height_threshold": self.fall_base_height_threshold,
            "fall_drop_margin_m": self.fall_drop_margin_m,
        }


def standing_height_params(
    grounded_spawn_z: float,
    *,
    fall_drop_margin_m: float = FALL_DROP_MARGIN_M,
) -> StandingHeightParams:
    """
    Derive aligned training heights from grounded spawn Z.

    Invariant: target_body_height == spawn_z (nominal stand).
    Invariant: fall_base_height_threshold == target - fall_drop_margin (must stay below target).
    """
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
    """Fall termination threshold for a given nominal target (same frame)."""
    return round(float(target_body_height) - float(fall_drop_margin_m), 4)


def assert_height_policy_consistent(params: StandingHeightParams) -> None:
    """Raise ValueError if spawn / target / fall violate the shared policy."""
    if params.target_body_height != params.spawn_z:
        raise ValueError(
            f"target_body_height ({params.target_body_height}) must equal spawn_z ({params.spawn_z})"
        )
    if params.fall_base_height_threshold >= params.target_body_height:
        raise ValueError(
            f"fall_base_height_threshold ({params.fall_base_height_threshold}) "
            f"must be below target_body_height ({params.target_body_height})"
        )
    expected = fall_threshold_for_target(params.target_body_height, fall_drop_margin_m=params.fall_drop_margin_m)
    if params.fall_base_height_threshold != expected:
        raise ValueError(
            f"fall_base_height_threshold ({params.fall_base_height_threshold}) expected {expected}"
        )


# Editor / template placeholder until geo spawn export is synced to the robot.
PLACEHOLDER_BODY_HEIGHT_M = 0.35
