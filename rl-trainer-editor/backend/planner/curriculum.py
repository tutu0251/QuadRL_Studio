"""Progressive training curricula — re-exports from curriculum_templates."""
from __future__ import annotations

from planner.curriculum_templates import (
    CURRICULUM_CATALOG,
    apply_curriculum_first_stage,
    build_stand_sprint_curriculum,
    curriculum_total_timesteps,
    get_curriculum_template,
    list_curricula,
)

__all__ = [
    "CURRICULUM_CATALOG",
    "apply_curriculum_first_stage",
    "build_stand_sprint_curriculum",
    "curriculum_total_timesteps",
    "get_curriculum_template",
    "list_curricula",
]
