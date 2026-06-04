"""Read/write action and observation scales in export YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from api.command_builder import build_training_config_patch_command
from domain.models import (
    ActionScaleEntry,
    ObservationScaleEntry,
    TerminationSummary,
    TrainingConfig,
    TrainingConfigUpdate,
)
from storage import monitor_storage, project_storage


def _load_yaml(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        return {}, ""
    raw = path.read_text(encoding="utf-8")
    header_lines = [line for line in raw.splitlines() if line.strip().startswith("#")]
    header = "\n".join(header_lines)
    if header:
        header += "\n"
    body = "\n".join(line for line in raw.splitlines() if not line.strip().startswith("#"))
    doc = yaml.safe_load(body) or {}
    return (doc if isinstance(doc, dict) else {}), header


def _save_yaml(path: Path, doc: dict[str, Any], header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + yaml.dump(doc, default_flow_style=False, sort_keys=False), encoding="utf-8")


def _termination_summary(termination: dict[str, Any], stage_name: str | None = None) -> TerminationSummary:
    terms = termination.get("termination_terms") or []
    enabled = [str(t.get("id", "")) for t in terms if t.get("enabled", True)]
    return TerminationSummary(
        stage_name=stage_name,
        max_episode_steps=int(termination.get("max_episode_steps", 1000)),
        fall_base_height_threshold=float(termination.get("fall_base_height_threshold", 0.1)),
        max_tilt_rad=float(termination.get("max_tilt_rad", 1.5)),
        enabled_term_ids=enabled,
    )


def get_training_config(name: str) -> TrainingConfig:
    gains_path = monitor_storage.gains_path(name)
    rl_path = project_storage.rl_config_path(name)

    gains_doc, _ = _load_yaml(gains_path)
    rl_doc, _ = _load_yaml(rl_path)

    action_scales: list[ActionScaleEntry] = []
    joints = gains_doc.get("joints") or {}
    for jname, spec in joints.items():
        if not isinstance(spec, dict):
            continue
        action_scales.append(
            ActionScaleEntry(
                joint=str(jname),
                action_scale=float(spec.get("action_scale", 0.25)),
                default_position=float(spec.get("default_position", 0.0)),
            )
        )
    action_scales.sort(key=lambda e: e.joint)

    observation_scales: list[ObservationScaleEntry] = []
    obs_block = rl_doc.get("observations") or {}
    for term in obs_block.get("terms") or []:
        if not isinstance(term, dict):
            continue
        observation_scales.append(
            ObservationScaleEntry(
                id=str(term.get("id", "")),
                key=str(term.get("key", "")),
                topic=str(term.get("topic") or ""),
                scale=float(term.get("scale", 1.0)),
                offset=float(term.get("offset", 0.0)),
                clip_min=float(term["clip_min"]) if term.get("clip_min") is not None else None,
                clip_max=float(term["clip_max"]) if term.get("clip_max") is not None else None,
                enabled=bool(term.get("enabled", True)),
            )
        )

    terminations: list[TerminationSummary] = []
    task = rl_doc.get("task") or {}
    if task.get("termination"):
        terminations.append(_termination_summary(task["termination"]))

    curriculum = rl_doc.get("curriculum") or {}
    if curriculum.get("enabled") and curriculum.get("stages"):
        for stage in curriculum["stages"]:
            if isinstance(stage, dict) and stage.get("termination"):
                terminations.append(
                    _termination_summary(stage["termination"], stage_name=str(stage.get("name", stage.get("id", ""))))
                )

    return TrainingConfig(
        project=name,
        gains_path=str(gains_path.relative_to(project_storage.project_dir(name)))
        if gains_path.is_file()
        else f"exports/ctrl_{name}_gains.yaml",
        rl_config_path=str(rl_path.relative_to(project_storage.project_dir(name)))
        if rl_path.is_file()
        else f"exports/rl_{name}_config.yaml",
        action_scales=action_scales,
        observation_scales=observation_scales,
        terminations=terminations,
        curriculum_enabled=bool(curriculum.get("enabled") and curriculum.get("stages")),
    )


def update_training_config(name: str, update: TrainingConfigUpdate) -> tuple[TrainingConfig, str]:
    touched: list[str] = []

    if update.action_scales:
        gains_path = monitor_storage.gains_path(name)
        doc, header = _load_yaml(gains_path)
        joints = doc.setdefault("joints", {})
        for entry in update.action_scales:
            spec = joints.setdefault(entry.joint, {})
            if isinstance(spec, dict):
                spec["action_scale"] = float(entry.action_scale)
        if not header:
            header = f"# Updated by Train Monitor — action scales\n"
        _save_yaml(gains_path, doc, header)
        touched.append(str(gains_path))

    if update.observation_scales:
        rl_path = project_storage.rl_config_path(name)
        doc, header = _load_yaml(rl_path)
        terms = (doc.get("observations") or {}).get("terms") or []
        by_id = {str(t.get("id")): t for t in terms if isinstance(t, dict)}
        for entry in update.observation_scales:
            term = by_id.get(entry.id)
            if not term:
                continue
            term["scale"] = float(entry.scale)
            term["offset"] = float(entry.offset)
            if entry.clip_min is not None:
                term["clip_min"] = float(entry.clip_min)
            if entry.clip_max is not None:
                term["clip_max"] = float(entry.clip_max)
        if not header:
            header = f"# Updated by Train Monitor — observation scales\n"
        _save_yaml(rl_path, doc, header)
        touched.append(str(rl_path))

    cfg = get_training_config(name)
    body = update.model_dump(exclude_none=True)
    command = build_training_config_patch_command(name, body)
    if touched:
        command = "# writes: " + ", ".join(touched) + "\n" + command
    return cfg, command
