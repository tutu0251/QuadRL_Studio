"""Auto-recommend gait, stage, and curriculum parameters."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import (
    CurriculumAdvanceCriteria,
    CurriculumStage,
    DisturbanceConfig,
    GaitType,
    MachineProfile,
    StageCommand,
    TerminationConfig,
)
from planner.gait_defaults import build_gait


@dataclass
class StageRecommendation:
    command: StageCommand
    disturbance: DisturbanceConfig
    timesteps: int
    termination: TerminationConfig
    advanceCriteria: CurriculumAdvanceCriteria
    notes: list[str]


_VEL_BY_GAIT = {
    "stand": 0.0,
    "recover": 0.0,
    "walk": 0.4,
    "trot": 0.8,
    "pace": 1.0,
    "bound": 1.2,
    "gallop": 1.5,
}

_TIMESTEPS_BY_GAIT = {
    "stand": 400_000,
    "recover": 350_000,
    "walk": 500_000,
    "trot": 550_000,
    "pace": 500_000,
    "bound": 550_000,
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


def recommend_stage_params(
    stage: CurriculumStage,
    rough: bool,
    machine: MachineProfile | None = None,
) -> StageRecommendation:
    gait_id = stage.gaitTypeId
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
        stage.targetLinVelX = rec.command.targetLinVelX
        notes.extend(rec.notes)
    return notes
