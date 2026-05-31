"""Helpers for stage gate-type (gait) selections."""
from __future__ import annotations

from domain.models import CurriculumStage
from planner.gait_defaults import resolve_gait_id

_LOCOMOTION_PRIORITY = ("gallop", "trot", "walk", "none")


def _dedupe_resolved(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for g in ids:
        c = resolve_gait_id(g)
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def stage_gait_type_ids(stage: CurriculumStage) -> list[str]:
    raw: list[str] = list(stage.gaitTypeIds) if stage.gaitTypeIds else []
    if not raw:
        legacy = getattr(stage, "gaitTypeId", None)
        if legacy:
            raw = [str(legacy)]
    resolved = _dedupe_resolved(raw)
    return resolved if resolved else ["none"]


def stage_is_stand_only(stage: CurriculumStage) -> bool:
    ids = stage_gait_type_ids(stage)
    return bool(ids) and all(g == "none" for g in ids)


def stage_primary_gait_for_command(stage: CurriculumStage) -> str:
    ids = stage_gait_type_ids(stage)
    if stage_is_stand_only(stage):
        return "none"
    for g in _LOCOMOTION_PRIORITY:
        if g in ids:
            return g
    return ids[0]

