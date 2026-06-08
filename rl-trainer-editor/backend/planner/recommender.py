"""Auto-recommend gait, stage, and curriculum parameters."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import (
    CurriculumAdvanceCriteria,
    CurriculumStage,
    DisturbanceConfig,
    GaitType,
    MachineProfile,
    RewardTerm,
    StageCommand,
    TerminationConfig,
    TerminationTerm,
)
from domain.stage_gait import stage_gait_type_ids, stage_is_stand_only, stage_primary_gait_for_command
from planner.gait_defaults import build_gait
from planner.reward_catalog import merge_reward_terms, recommend_reward_terms_for_stage
from planner.standing_heights import PLACEHOLDER_BODY_HEIGHT_M, heights_for_target
from planner.termination_catalog import (
    merge_termination_config,
    recommend_termination_terms_for_stage,
)


@dataclass
class StageRecommendation:
    command: StageCommand
    disturbance: DisturbanceConfig
    timesteps: int
    termination: TerminationConfig
    advanceCriteria: CurriculumAdvanceCriteria
    paramEnabled: dict[str, bool]
    rewardTerms: list[RewardTerm]
    notes: list[str]


_VEL_BY_GAIT = {
    "none": 0.0,
    "walk": 0.5,
    "trot": 0.8,
    "pace": 1.0,
    "bound": 1.2,
    "gallop": 1.4,
}

_TIMESTEPS_BY_GAIT = {
    "none": 400_000,
    "walk": 550_000,
    "trot": 600_000,
    "pace": 600_000,
    "bound": 650_000,
    "gallop": 700_000,
}


def _machine_scale(machine: MachineProfile | None) -> float:
    if not machine:
        return 1.0
    if machine.ramGb >= 32:
        return 1.2
    if machine.ramGb >= 16:
        return 1.0
    if machine.ramGb >= 8:
        return 0.85
    return 0.7


def recommend_gait(gait_id: str) -> tuple[GaitType, list[str]]:
    gait = build_gait(gait_id)
    notes = [f"Applied canonical parameters for gait '{gait.name}'."]
    return gait, notes


def _recommend_reward_terms(stage: CurriculumStage) -> list[RewardTerm]:
    is_stand = stage_is_stand_only(stage)
    merged = merge_reward_terms(stage.rewardTerms)
    vel = stage.command.targetLinVelX
    return recommend_reward_terms_for_stage(
        merged,
        stage.command,
        is_stand=is_stand,
        lin_vel_scale=abs(vel),
    )


def recommend_param_enabled(
    stage: CurriculumStage,
    rough: bool,
    reward_terms: list[RewardTerm],
    termination_terms: list[TerminationTerm] | None = None,
    disturbance: DisturbanceConfig | None = None,
) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    is_stand = stage_is_stand_only(stage)

    for key in ("name", "description", "gait_type", "timesteps"):
        flags[f"identity.{key}"] = True

    cmd = stage.command
    for key in (
        "target_lin_vel_x",
        "target_lin_vel_y",
        "target_ang_vel_z",
        "target_body_height",
        "gait_speed_scale",
    ):
        flags[f"command.{key}"] = True
    if is_stand:
        flags["command.target_lin_vel_y"] = False
        flags["command.target_ang_vel_z"] = False
    if cmd.targetLinVelY == 0:
        flags["command.target_lin_vel_y"] = False
    if cmd.targetAngVelZ == 0:
        flags["command.target_ang_vel_z"] = False

    # Mark the disturbance params active when the stage actually has disturbances
    # enabled, so the editor's per-param checkboxes match the live values. Falling
    # back to `rough` (the old behavior) left perturbed-but-flat stages showing
    # unchecked boxes even though training applies the values.
    dist_on = bool(disturbance.enabled) if disturbance is not None else rough
    flags["disturbance.enabled"] = dist_on
    for key in (
        "push_force_n",
        "push_interval_steps",
        "terrain_roughness",
        "lateral_impulse_n",
        "orientation_noise_rad",
    ):
        flags[f"disturbance.{key}"] = dist_on

    for key in (
        "max_episode_steps",
        "fall_base_height_threshold",
        "max_tilt_rad",
        "max_joint_torque",
        "timeout_truncation",
    ):
        flags[f"termination.{key}"] = True
    flags["termination.max_joint_torque"] = stage.termination.maxJointTorque is not None

    for key in (
        "min_mean_episode_reward",
        "min_episode_length_frac",
        "max_fall_rate",
    ):
        flags[f"advance.{key}"] = True

    for term in reward_terms:
        flags[f"reward.{term.id}.weight"] = term.enabled
        for pk in term.params:
            active = term.enabled
            if pk == "target_ang_vel_z" and cmd.targetAngVelZ == 0:
                active = False
            if pk == "target_lin_vel_y":
                active = False
            flags[f"reward.{term.id}.{pk}"] = active

    for term in termination_terms or stage.termination.terminationTerms:
        for pk in term.params:
            flags[f"termination.{term.id}.{pk}"] = term.enabled

    return flags


def recommend_stage_params(
    stage: CurriculumStage,
    rough: bool,
    machine: MachineProfile | None = None,
) -> StageRecommendation:
    gait_id = stage_primary_gait_for_command(stage)
    selected = stage_gait_type_ids(stage)
    # Honor the stage's authored command velocity / timesteps; fall back to
    # gait-based defaults only when the stage leaves them unset. Alias gaits
    # collapse under the catalog (pace -> trot, bound -> gallop), so deriving
    # speed purely from the resolved gait would discard a stage's intended
    # velocity and force aliased stages to the same value.
    vel = stage.targetLinVelX
    if not vel:
        vel = max(_VEL_BY_GAIT.get(g, 0.0) for g in selected) if selected else 0.0
        if gait_id in _VEL_BY_GAIT:
            vel = _VEL_BY_GAIT[gait_id]
    scale = _machine_scale(machine)
    base_ts = stage.timesteps
    if not base_ts:
        base_ts = max(_TIMESTEPS_BY_GAIT.get(g, 0) for g in selected) if selected else 0
        if gait_id in _TIMESTEPS_BY_GAIT:
            base_ts = _TIMESTEPS_BY_GAIT[gait_id]
    timesteps = max(50_000, int(base_ts * scale * (1.1 if rough else 1.0)))

    # Height policy follows spawn / command target (base_link Z), not gait kinematics bodyHeight.
    nominal_h = float(stage.command.targetBodyHeight or PLACEHOLDER_BODY_HEIGHT_M)
    heights = heights_for_target(nominal_h)
    cmd = StageCommand(
        targetLinVelX=vel,
        targetLinVelY=0.0,
        targetAngVelZ=0.0,
        targetBodyHeight=heights.target_body_height,
        gaitSpeedScale=1.0 + stage.order * 0.05,
    )

    # Graduated perturbations teach closed-loop recovery. Stand stays a clean
    # balance baseline (no pushes); perturbations ramp from Recover (order 1)
    # through Gallop (order 6) so the policy learns to resist its own action
    # noise and external shoves instead of memorizing one precise pose. The
    # wrench engine (training/quadrl_env/disturbances.py) consumes pushForceN /
    # pushIntervalSteps / lateralImpulseN; terrainRoughness is layered on only for
    # the rough-terrain curriculum. Forces are absolute N (robot body weight is
    # ~79 N), so 15→40 N spans ~19%–50% of weight. _build_stage overwrites the
    # template's placeholder stage.disturbance with this output.
    is_stand = stage_is_stand_only(stage)
    # Only the initial balance stage (order 0 / Stand) is a clean baseline.
    # Recover is also zero-velocity (stage_is_stand_only would be True), but it
    # is the recovery stage and MUST be perturbed — so gate on order, not is_stand.
    if stage.order <= 0:
        disturbance = DisturbanceConfig()
    else:
        frac = min(1.0, (stage.order - 1) / 5.0)  # 0 at Recover, 1 at Gallop
        roughness = min(0.85, 0.15 + stage.order * 0.1)
        disturbance = DisturbanceConfig(
            enabled=True,
            pushForceN=round(15 + frac * 25, 1),         # 15 → 40 N
            pushIntervalSteps=int(150 - frac * 70),      # ~every 3.0 s → 1.6 s at 50 Hz
            lateralImpulseN=round(8 + frac * 14, 1),     # 8 → 22 N
            terrainRoughness=round(roughness * 0.8, 3) if rough else 0.0,
            randomOrientationNoiseRad=round(0.02 + frac * 0.04, 3),
        )
    termination = merge_termination_config(stage.termination)
    termination.maxEpisodeSteps = 800 + stage.order * 200
    termination.fallBaseHeightThreshold = heights.fall_base_height_threshold
    termination.maxTiltRad = min(1.2, 0.75 + stage.order * 0.06)
    termination.terminationTerms = recommend_termination_terms_for_stage(
        termination.terminationTerms,
        cmd,
        is_stand=is_stand,
        lin_vel_scale=abs(vel),
        rough=rough,
    )
    advance = CurriculumAdvanceCriteria(
        minMeanEpisodeReward=max(0.25, 0.65 - stage.order * 0.06),
        minEpisodeLengthFrac=max(0.65, 0.90 - stage.order * 0.04),
        maxFallRate=min(0.20, 0.08 + stage.order * 0.02),
    )
    reward_terms = _recommend_reward_terms(stage)
    param_enabled = recommend_param_enabled(
        stage, rough, reward_terms, termination.terminationTerms, disturbance
    )
    notes = [
        f"Recommended stage '{stage.name}': vel={vel:.2f} m/s, "
        f"timesteps={timesteps:,}, rough={rough}."
    ]
    return StageRecommendation(
        command=cmd,
        disturbance=disturbance,
        timesteps=timesteps,
        termination=termination,
        advanceCriteria=advance,
        paramEnabled=param_enabled,
        rewardTerms=reward_terms,
        notes=notes,
    )


def recommend_curriculum_timesteps(
    stages: list[CurriculumStage],
    rough: bool,
    machine: MachineProfile | None = None,
) -> list[str]:
    notes: list[str] = []
    for stage in stages:
        rec = recommend_stage_params(stage, rough, machine)
        stage.timesteps = rec.timesteps
        stage.command = rec.command
        stage.disturbance = rec.disturbance
        stage.termination = rec.termination
        stage.advanceCriteria = rec.advanceCriteria
        stage.rewardTerms = rec.rewardTerms
        stage.paramEnabled = rec.paramEnabled
        stage.targetLinVelX = rec.command.targetLinVelX
        notes.extend(rec.notes)
    return notes
