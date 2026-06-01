"""Tests for termination catalog merge and export."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import StageCommand, TerminationConfig, TerminationTerm
from planner.termination_catalog import (
    TERMINATION_CATALOG,
    build_full_termination_catalog,
    merge_termination_config,
    merge_termination_terms,
    recommend_termination_terms_for_stage,
)


def test_catalog_has_seven_terms():
    assert len(TERMINATION_CATALOG) == 7
    ids = {e.id for e in TERMINATION_CATALOG}
    assert "foot_slip_contact_loss" in ids
    assert "reward_anomaly" in ids


def test_merge_adds_missing_catalog_entries():
    merged = merge_termination_terms([])
    assert len(merged) == 7
    assert all(not t.enabled for t in merged)


def test_merge_termination_config_preserves_globals():
    cfg = TerminationConfig(maxEpisodeSteps=42, terminationTerms=[])
    out = merge_termination_config(cfg)
    assert out.maxEpisodeSteps == 42
    assert len(out.terminationTerms) == 7


def test_recommend_enables_locomotion_velocity_limits():
    terms = recommend_termination_terms_for_stage(
        [],
        StageCommand(targetLinVelX=0.8),
        is_stand=False,
        lin_vel_scale=0.8,
    )
    by_id = {t.id: t for t in terms}
    assert by_id["base_linear_velocity_limit"].enabled
    assert not by_id["reward_anomaly"].enabled


def test_recommend_rough_enables_reward_anomaly():
    terms = recommend_termination_terms_for_stage(
        [],
        StageCommand(targetLinVelX=0.8),
        is_stand=False,
        rough=True,
    )
    assert any(t.id == "reward_anomaly" and t.enabled for t in terms)


def test_custom_term_params_preserved_on_merge():
    custom = TerminationTerm(
        id="foot_slip_contact_loss",
        category="contact",
        enabled=True,
        params={"slip_threshold": 0.5, "min_contacts": 2, "contact_loss_steps": 5},
    )
    merged = merge_termination_terms([custom])
    term = next(t for t in merged if t.id == "foot_slip_contact_loss")
    assert term.params["slip_threshold"] == 0.5
    assert term.enabled is True
