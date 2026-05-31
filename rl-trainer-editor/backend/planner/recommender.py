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
)
from planner.gait_defaults import build_gait, resolve_gait_id


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


_STAND_REWARD_IDS = frozenset(
    {"base_height", "orientation_upright", "foot_contact", "velocity_penalty"}
)
_LOCO_REWARD_IDS = frozenset(
    {
        "lin_vel_tracking",
        "ang_vel_tracking",
        "orientation_penalty",
        "torque_penalty",
        "base_height",
        "gait_symmetry",
    }
)


_VEL_BY_GAIT = {
    "none": 0.0,
    "walk": 0.4,
    "trot": 0.8,
    "gallop": 1.5,
}

_TIMESTEPS_BY_GAIT = {
    "none": 400_000,
    "walk": 500_000,
    "trot": 550_000,
    "gallop": 650_000,
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
    is_stand = resolve_gait_id(stage.gaitTypeId) == "none"
    out: list[RewardTerm] = []
    for term in stage.rewardTerms:
        t = term.model_copy(deep=True)
        if is_stand:
            t.enabled = term.id in _STAND_REWARD_IDS
        else:
            t.enabled = term.id in _LOCO_REWARD_IDS
        out.append(t)
    return out


def recommend_param_enabled(
    stage: CurriculumStage,
    rough: bool,
    reward_terms: list[RewardTerm],
) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    is_stand = resolve_gait_id(stage.gaitTypeId) == "none"

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

    flags["disturbance.enabled"] = rough
    for key in (
        "push_force_n",
        "push_interval_steps",
        "terrain_roughness",
        "lateral_impulse_n",
        "orientation_noise_rad",
    ):
        flags[f"disturbance.{key}"] = rough

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

    return flags


def recommend_stage_params(
    stage: CurriculumStage,
    rough: bool,
    machine: MachineProfile | None = None,
) -> StageRecommendation:
    gait_id = resolve_gait_id(stage.gaitTypeId)
    vel = _VEL_BY_GAIT.get(gait_id, stage.targetLinVelX)
    scale = _machine_scale(machine)
    base_ts = _TIMESTEPS_BY_GAIT.get(gait_id, stage.timesteps)
    timesteps = max(50_000, int(base_ts * scale * (1.1 if rough else 1.0)))

    gait = build_gait(gait_id) if gait_id in _VEL_BY_GAIT else None
    cmd = StageCommand(
        targetLinVelX=vel,
        targetLinVelY=0.0,
        targetAngVelZ=0.0,
        targetBodyHeight=gait.bodyHeight if gait and gait.bodyHeight else 0.35,
        gaitSpeedScale=1.0 + stage.order * 0.05,
    )

    disturbance = stage.disturbance.model_copy(deep=True)
    if rough:
        roughness = min(0.85, 0.15 + stage.order * 0.1)
        disturbance = DisturbanceConfig(
            enabled=True,
            pushForceN=15 + roughness * 30,
            pushIntervalSteps=max(300, int(800 - roughness * 400)),
            terrainRoughness=roughness,
            lateralImpulseN=5 + roughness * 15,
            randomOrientationNoiseRad=0.02 + roughness * 0.06,
        )
    else:
        disturbance = DisturbanceConfig()

    termination = TerminationConfig(
        maxEpisodeSteps=500 + stage.order * 150,
        fallBaseHeightThreshold=0.12,
        maxTiltRad=min(0.85, 0.55 + stage.order * 0.04),
    )
    advance = CurriculumAdvanceCriteria(
        minMeanEpisodeReward=max(0.2, 0.55 - stage.order * 0.05),
        minEpisodeLengthFrac=max(0.55, 0.85 - stage.order * 0.04),
        maxFallRate=min(0.35, 0.15 + stage.order * 0.03),
    )
    reward_terms = _recommend_reward_terms(stage)
    param_enabled = recommend_param_enabled(stage, rough, reward_terms)
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
