"""Export unified RL training config for SB3 + ROS2/Gazebo."""
from __future__ import annotations

from pathlib import Path

import yaml

from domain.models import CurriculumConfig, CurriculumStage, GaitType, RlTrainerModel
from domain.stage_gait import stage_gait_type_ids
from planner.curriculum import curriculum_total_timesteps
from storage import project_storage


def _termination_term_export(term) -> dict:
    return {
        "id": term.id,
        "category": term.category,
        "enabled": term.enabled,
        "params": dict(term.params),
    }


def _termination_export(t) -> dict:
    return {
        "max_episode_steps": t.maxEpisodeSteps,
        "fall_base_height_threshold": t.fallBaseHeightThreshold,
        "max_tilt_rad": t.maxTiltRad,
        "max_joint_torque": t.maxJointTorque,
        "timeout_truncation": t.timeoutTruncation,
        "termination_terms": [_termination_term_export(term) for term in t.terminationTerms],
    }


def _advance_criteria_export(c) -> dict:
    return {
        "min_mean_episode_reward": c.minMeanEpisodeReward,
        "min_episode_length_frac": c.minEpisodeLengthFrac,
        "max_fall_rate": c.maxFallRate,
        "min_timesteps_in_stage": c.minTimestepsInStage,
    }


def _disturbance_export(d) -> dict:
    return {
        "enabled": d.enabled,
        "push_force_n": d.pushForceN,
        "push_interval_steps": d.pushIntervalSteps,
        "terrain_roughness": d.terrainRoughness,
        "lateral_impulse_n": d.lateralImpulseN,
        "random_orientation_noise_rad": d.randomOrientationNoiseRad,
    }


def _command_export(stage: CurriculumStage) -> dict:
    cmd = stage.command
    return {
        "target_lin_vel_x": cmd.targetLinVelX,
        "target_lin_vel_y": cmd.targetLinVelY,
        "target_ang_vel_z": cmd.targetAngVelZ,
        "target_body_height": cmd.targetBodyHeight,
        "gait_speed_scale": cmd.gaitSpeedScale,
    }


def _stage_export(stage: CurriculumStage) -> dict:
    return {
        "id": stage.id,
        "name": stage.name,
        "order": stage.order,
        "description": stage.description,
        "timesteps": stage.timesteps,
        "gait_type_ids": stage_gait_type_ids(stage),
        "gait_type_id": stage_gait_type_ids(stage)[0],
        "command": _command_export(stage),
        "disturbance": _disturbance_export(stage.disturbance),
        "reward_terms": [_reward_term_export(t) for t in stage.rewardTerms],
        "termination": _termination_export(stage.termination),
        "advance_criteria": _advance_criteria_export(stage.advanceCriteria),
        "param_enabled": dict(stage.paramEnabled),
    }


def _gait_export(gait: GaitType) -> dict:
    return {
        "id": gait.id,
        "name": gait.name,
        "builtin": gait.builtin,
        "cycle_time": gait.cycleTime,
        "duty_factor": gait.dutyFactor,
        "phase_offsets": {
            "fl": gait.phaseOffsets.fl,
            "fr": gait.phaseOffsets.fr,
            "rl": gait.phaseOffsets.rl,
            "rr": gait.phaseOffsets.rr,
        },
        "swing_height": gait.swingHeight,
        "step_length": gait.stepLength,
        "body_height": gait.bodyHeight,
    }


def _curriculum_export(cur: CurriculumConfig) -> dict:
    stages = sorted(cur.stages, key=lambda s: s.order)
    return {
        "enabled": cur.enabled,
        "curriculum_id": cur.curriculumId,
        "name": cur.name,
        "description": cur.description,
        "terrain_profile": cur.terrainProfile,
        "current_stage_index": cur.currentStageIndex,
        "load_previous_checkpoint": cur.loadPreviousCheckpoint,
        "reset_policy_on_stage_advance": cur.resetPolicyOnStageAdvance,
        "total_timesteps": curriculum_total_timesteps(cur),
        "stages": [_stage_export(s) for s in stages],
    }


def _training_export(model: RlTrainerModel) -> dict:
    tc = model.trainingCheckpoint
    return {
        "resume_checkpoint": tc.resumeCheckpointPath,
        "start_from_scratch": tc.resumeCheckpointPath is None,
        "checkpoint_directory": tc.checkpointDirectory,
    }


def _reward_term_export(term) -> dict:
    return {
        "id": term.id,
        "type": term.type,
        "category": term.category,
        "weight": term.weight,
        "enabled": term.enabled,
        "params": dict(term.params),
    }


def export_rl_yaml(model: RlTrainerModel, project_name: str) -> Path:
    out = project_storage.export_rl_yaml_path(project_name)
    out.parent.mkdir(parents=True, exist_ok=True)

    t = model.termination

    body = {
        "algorithm": "PPO",
        "framework": "stable_baselines3",
        "project": project_name,
        "robot": model.robotName,
        "ppo_config_file": f"ppo_{project_name}_config.yaml",
        "env": {
            "observations_file": f"sens_{project_name}_observations.yaml",
            "gains_file": f"ctrl_{project_name}_gains.yaml",
            "sim_urdf": f"sens_{project_name}_rl.urdf",
        },
        "task": {
            "preset_id": model.selectedPresetId,
            "reward_terms": [_reward_term_export(term) for term in model.rewardTerms],
            "termination": _termination_export(t),
        },
        "gait_types": [_gait_export(g) for g in model.gaitTypes],
        "training": _training_export(model),
        "curriculum": _curriculum_export(model.curriculum),
        "logging": {
            "tensorboard_root": "runs",
            "tensorboard_note": (
                "Training writes runs/<timestamp>/run_info.yaml; curriculum stages log to "
                "runs/<timestamp>/<order>_<stage_id>_<name>/ (SB3 PPO_* subdirs inside)."
            ),
        },
        "custom_params": dict(model.customParams),
        "machine_profile": model.machineProfile.model_dump() if model.machineProfile else None,
        "recommendation_notes": model.recommendationNotes,
    }

    header = (
        f"# Auto-generated by QuadRL RL Trainer Editor\n"
        f"# Project: {project_name}\n"
        f"# PPO hyperparameters and parallel envs: export from PPO Planner ({body['ppo_config_file']})\n"
    )
    out.write_text(header + yaml.dump(body, default_flow_style=False, sort_keys=False))
    return out
