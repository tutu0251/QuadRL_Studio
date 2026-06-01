"""Recommend observation selection from reward configuration."""
from __future__ import annotations

from domain.models import ObservationTerm, RlTrainerModel
from planner.observation_catalog import merge_observation_terms, recommend_observation_terms


def _enabled_reward_categories(model: RlTrainerModel) -> set[str]:
    categories: set[str] = set()
    if model.curriculum.enabled and model.curriculum.stages:
        idx = model.curriculum.currentStageIndex
        stages = sorted(model.curriculum.stages, key=lambda s: s.order)
        if 0 <= idx < len(stages):
            for term in stages[idx].rewardTerms:
                if term.enabled:
                    categories.add(term.category)
    for term in model.rewardTerms:
        if term.enabled:
            categories.add(term.category)
    return categories


def sync_observations(model: RlTrainerModel) -> RlTrainerModel:
    model.observationTerms = merge_observation_terms(
        model.observationTerms,
        model.projectName,
    )
    return model


def apply_observation_recommendation(model: RlTrainerModel) -> tuple[RlTrainerModel, list[str]]:
    model = sync_observations(model)
    categories = _enabled_reward_categories(model)
    if not categories:
        categories = {"velocity", "orientation", "contact", "action_smoothness"}
    terms, notes = recommend_observation_terms(
        model.observationTerms,
        reward_categories=categories,
    )
    model.observationTerms = terms
    return model, notes
