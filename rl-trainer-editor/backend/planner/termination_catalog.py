"""Canonical termination condition catalog with recommended thresholds."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import StageCommand, TerminationConfig, TerminationTerm

TERMINATION_CATALOG_VERSION = "1"


@dataclass(frozen=True)
class TerminationParamSpec:
    key: str
    recommended: float
    minimum: float
    maximum: float
    step: float = 0.01


@dataclass(frozen=True)
class TerminationCatalogEntry:
    id: str
    label: str
    category: str
    params: tuple[TerminationParamSpec, ...]


def _p(key: str, rec: float, lo: float, hi: float, step: float = 0.01) -> TerminationParamSpec:
    return TerminationParamSpec(key=key, recommended=rec, minimum=lo, maximum=hi, step=step)


TERMINATION_CATALOG: tuple[TerminationCatalogEntry, ...] = (
    TerminationCatalogEntry(
        "foot_slip_contact_loss",
        "Foot slip / contact loss",
        "contact",
        (
            _p("slip_threshold", 0.25, 0.05, 1.0),
            _p("min_contacts", 1, 1, 4, 1),
            _p("contact_loss_steps", 3, 1, 30, 1),
        ),
    ),
    TerminationCatalogEntry(
        "base_linear_velocity_limit",
        "Base linear velocity limit",
        "velocity",
        (_p("max_lin_vel", 3.0, 0.5, 8.0, 0.1),),
    ),
    TerminationCatalogEntry(
        "base_angular_velocity_limit",
        "Base angular velocity limit",
        "velocity",
        (_p("max_ang_vel", 5.0, 1.0, 15.0, 0.1),),
    ),
    TerminationCatalogEntry(
        "joint_limits_self_collision",
        "Joint limits / self-collision",
        "safety",
        (_p("limit_margin", 0.05, 0.01, 0.2, 0.005),),
    ),
    TerminationCatalogEntry(
        "energy_torque_safety",
        "Energy / torque safety",
        "energy",
        (
            _p("max_joint_torque", 80, 10, 200, 1),
            _p("max_joint_power", 500, 50, 2000, 10),
        ),
    ),
    TerminationCatalogEntry(
        "height_deviation_terrain_contact",
        "Height deviation / terrain contact",
        "height",
        (
            _p("max_height_deviation", 0.12, 0.03, 0.4),
            _p("min_terrain_contacts", 1, 0, 4, 1),
        ),
    ),
    TerminationCatalogEntry(
        "reward_anomaly",
        "Excessive episode reward anomaly",
        "monitoring",
        (
            _p("max_step_reward", 5.0, 0.5, 50, 0.5),
            _p("cumulative_threshold", 100, 10, 500, 5),
        ),
    ),
)

_CATALOG_BY_ID = {e.id: e for e in TERMINATION_CATALOG}

_STAND_ENABLE = frozenset(
    {
        "foot_slip_contact_loss",
        "joint_limits_self_collision",
        "energy_torque_safety",
    }
)

_LOCO_ENABLE = frozenset(
    {
        "foot_slip_contact_loss",
        "base_linear_velocity_limit",
        "base_angular_velocity_limit",
        "joint_limits_self_collision",
        "energy_torque_safety",
        "height_deviation_terrain_contact",
    }
)


def catalog_entry(term_id: str) -> TerminationCatalogEntry | None:
    return _CATALOG_BY_ID.get(term_id)


def build_catalog_term(entry: TerminationCatalogEntry, *, enabled: bool = False) -> TerminationTerm:
    params = {s.key: s.recommended for s in entry.params}
    return TerminationTerm(
        id=entry.id,
        category=entry.category,
        enabled=enabled,
        params=params,
    )


def build_full_termination_catalog(*, enabled_ids: frozenset[str] | None = None) -> list[TerminationTerm]:
    out: list[TerminationTerm] = []
    for entry in TERMINATION_CATALOG:
        enabled = enabled_ids is not None and entry.id in enabled_ids
        out.append(build_catalog_term(entry, enabled=enabled))
    return out


def _clamp_param(key: str, value: float, entry: TerminationCatalogEntry) -> float:
    for spec in entry.params:
        if spec.key == key:
            return max(spec.minimum, min(spec.maximum, value))
    return value


def recommend_term_params(
    term: TerminationTerm,
    cmd: StageCommand,
    *,
    lin_vel_scale: float = 1.0,
) -> TerminationTerm:
    entry = catalog_entry(term.id)
    if not entry:
        return term
    t = term.model_copy(deep=True)
    if entry.id == "base_linear_velocity_limit":
        t.params["max_lin_vel"] = _clamp_param(
            "max_lin_vel",
            max(1.5, 2.0 + lin_vel_scale * 1.2),
            entry,
        )
    if entry.id == "height_deviation_terrain_contact":
        t.params["max_height_deviation"] = _clamp_param(
            "max_height_deviation",
            max(0.08, 0.1 + abs(cmd.targetBodyHeight) * 0.15),
            entry,
        )
    for spec in entry.params:
        if spec.key not in t.params:
            t.params[spec.key] = spec.recommended
        else:
            t.params[spec.key] = _clamp_param(spec.key, t.params[spec.key], entry)
    return t


def merge_termination_terms(existing: list[TerminationTerm] | None) -> list[TerminationTerm]:
    by_id: dict[str, TerminationTerm] = {}
    for term in existing or []:
        entry = catalog_entry(term.id)
        if not entry:
            continue
        t = term.model_copy(deep=True)
        t.category = entry.category
        for spec in entry.params:
            if spec.key not in t.params:
                t.params[spec.key] = spec.recommended
        by_id[entry.id] = t
    out: list[TerminationTerm] = []
    for entry in TERMINATION_CATALOG:
        if entry.id in by_id:
            out.append(by_id[entry.id])
        else:
            out.append(build_catalog_term(entry, enabled=False))
    return out


def recommend_termination_terms_for_stage(
    stage_terms: list[TerminationTerm] | None,
    cmd: StageCommand,
    *,
    is_stand: bool,
    lin_vel_scale: float = 1.0,
    rough: bool = False,
) -> list[TerminationTerm]:
    merged = merge_termination_terms(stage_terms)
    enable = _STAND_ENABLE if is_stand else _LOCO_ENABLE
    if rough:
        enable = enable | frozenset({"reward_anomaly"})
    out: list[TerminationTerm] = []
    for term in merged:
        t = term.model_copy(deep=True)
        t.enabled = term.id in enable
        t = recommend_term_params(t, cmd, lin_vel_scale=lin_vel_scale)
        out.append(t)
    return out


def merge_termination_config(config: TerminationConfig | None) -> TerminationConfig:
    base = config.model_copy(deep=True) if config else TerminationConfig()
    base.terminationTerms = merge_termination_terms(base.terminationTerms)
    return base


def list_catalog_export() -> list[dict]:
    rows: list[dict] = []
    for entry in TERMINATION_CATALOG:
        rows.append(
            {
                "id": entry.id,
                "label": entry.label,
                "category": entry.category,
                "params": [
                    {
                        "key": p.key,
                        "recommended": p.recommended,
                        "min": p.minimum,
                        "max": p.maximum,
                        "step": p.step,
                    }
                    for p in entry.params
                ],
            }
        )
    return rows
