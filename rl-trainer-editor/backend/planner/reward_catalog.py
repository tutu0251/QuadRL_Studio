"""Canonical reward/penalty catalog with recommended weights and param ranges."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import RewardTerm, StageCommand
from planner.standing_heights import PLACEHOLDER_BODY_HEIGHT_M

REWARD_CATALOG_VERSION = "1"


@dataclass(frozen=True)
class RewardParamSpec:
    key: str
    recommended: float
    minimum: float
    maximum: float
    step: float = 0.01


@dataclass(frozen=True)
class RewardCatalogEntry:
    id: str
    type: str
    category: str
    recommended_weight: float
    params: tuple[RewardParamSpec, ...]


def _p(key: str, rec: float, lo: float, hi: float, step: float = 0.01) -> RewardParamSpec:
    return RewardParamSpec(key=key, recommended=rec, minimum=lo, maximum=hi, step=step)


REWARD_CATALOG: tuple[RewardCatalogEntry, ...] = (
    # —— Rewards ——
    RewardCatalogEntry("alive", "reward", "survival", 0.25, ()),
    RewardCatalogEntry(
        "upright",
        "reward",
        "orientation",
        0.8,
        (_p("sigma", 0.12, 0.03, 0.4),),
    ),
    RewardCatalogEntry(
        "height",
        "reward",
        "height",
        1.0,
        (
            _p("target_height", PLACEHOLDER_BODY_HEIGHT_M, 0.2, 0.5, 0.01),
            _p("sigma", 0.06, 0.02, 0.2),
        ),
    ),
    RewardCatalogEntry(
        "posture",
        "reward",
        "posture",
        0.5,
        (_p("sigma", 0.15, 0.05, 0.5),),
    ),
    RewardCatalogEntry(
        "contact",
        "reward",
        "contact",
        0.35,
        (
            _p("min_contacts", 2, 1, 4, 1),
            _p("sigma", 0.2, 0.05, 0.6),
        ),
    ),
    RewardCatalogEntry(
        "forward_tracking",
        "reward",
        "velocity",
        # Dominant locomotion reward. Survival terms (upright+height+posture+...) sum
        # to ~3 and are earnable while standing still, so a weight of 1.0 let the
        # policy collapse into a "balance in place" optimum and ignore the velocity
        # command. Raised so hitting target speed clearly out-earns standing.
        2.2,
        (_p("sigma", 0.22, 0.08, 0.6),),
    ),
    RewardCatalogEntry(
        # Linear forward-progress reward — complements forward_tracking. The Gaussian
        # forward_tracking gives a comfortable ~0.16 floor at standstill and saturates,
        # so a balanced policy can sit at "stand in place"; this linear ramp earns 0
        # while still and rises with forward speed, supplying the gradient that pushes
        # the policy off the standing attractor. No params (target comes from command).
        "forward_progress",
        "reward",
        "velocity",
        # Moderated from 1.5 -> 0.8 after the first attempt overshot: combined with
        # forward_tracking (2.2) the per-step velocity payoff was high enough that a
        # forward LUNGE out-earned a stable walk even though the episode ended in a
        # fall. Kept positive so the no-plateau gradient still pulls off standing.
        0.8,
        (),
    ),
    RewardCatalogEntry(
        "lateral_tracking",
        "reward",
        "velocity",
        0.6,
        (_p("sigma", 0.18, 0.06, 0.5),),
    ),
    RewardCatalogEntry(
        "yaw_tracking",
        "reward",
        "velocity",
        0.5,
        (_p("sigma", 0.2, 0.08, 0.55),),
    ),
    RewardCatalogEntry(
        "diagonal_balance",
        "reward",
        "gait",
        0.25,
        (_p("sigma", 0.15, 0.05, 0.45),),
    ),
    RewardCatalogEntry(
        "air_time",
        "reward",
        "gait",
        0.15,
        (
            _p("target_air_time", 0.12, 0.04, 0.35, 0.01),
            _p("sigma", 0.08, 0.02, 0.25),
        ),
    ),
    RewardCatalogEntry(
        "foot_clearance",
        "reward",
        "gait",
        0.2,
        (
            _p("min_clearance", 0.04, 0.01, 0.12, 0.005),
            _p("sigma", 0.03, 0.01, 0.1),
        ),
    ),
    # —— Penalties ——
    RewardCatalogEntry(
        "angular_velocity",
        "penalty",
        "velocity",
        -0.25,
        (_p("sigma", 0.15, 0.05, 0.5),),
    ),
    RewardCatalogEntry(
        "linear_velocity",
        "penalty",
        "velocity",
        -0.35,
        (_p("sigma", 0.1, 0.03, 0.35),),
    ),
    RewardCatalogEntry(
        "z_velocity",
        "penalty",
        "velocity",
        -0.2,
        (_p("sigma", 0.08, 0.02, 0.3),),
    ),
    RewardCatalogEntry(
        "joint_velocity",
        "penalty",
        "energy",
        -0.00015,
        (_p("sigma", 1.0, 0.1, 5.0, 0.1),),
    ),
    RewardCatalogEntry(
        "action_velocity",
        "penalty",
        "action_smoothness",
        -0.03,
        (_p("sigma", 0.12, 0.04, 0.4),),
    ),
    RewardCatalogEntry(
        "action_rate",
        "penalty",
        "action_smoothness",
        -0.05,
        (_p("sigma", 0.1, 0.03, 0.35),),
    ),
    RewardCatalogEntry(
        "posture_penalty",
        "penalty",
        "posture",
        -0.4,
        (_p("sigma", 0.1, 0.03, 0.4),),
    ),
    RewardCatalogEntry(
        "target_posture",
        "penalty",
        "posture",
        # Softened: pinning the body to a static reference posture fights the
        # leg-cycling needed to walk, reinforcing the stand-in-place optimum.
        -0.2,
        (_p("sigma", 0.12, 0.04, 0.45),),
    ),
    RewardCatalogEntry(
        "smoothness",
        "penalty",
        "action_smoothness",
        -0.05,
        (_p("sigma", 0.1, 0.03, 0.35),),
    ),
    RewardCatalogEntry(
        "contact_balance",
        "penalty",
        "contact",
        -0.15,
        (_p("sigma", 0.2, 0.05, 0.6),),
    ),
    RewardCatalogEntry(
        "contact_switch",
        "penalty",
        "contact",
        -0.1,
        (
            _p("max_switches_per_step", 2, 1, 4, 1),
            _p("sigma", 0.25, 0.08, 0.7),
        ),
    ),
    RewardCatalogEntry(
        "target_like",
        "penalty",
        "tracking",
        -0.1,
        (_p("sigma", 0.18, 0.06, 0.5),),
    ),
    RewardCatalogEntry(
        "stumble",
        "penalty",
        "contact",
        -0.12,
        (
            _p("threshold", 35.0, 10.0, 120.0, 1),
            _p("sigma", 15.0, 5.0, 50.0, 1),
        ),
    ),
    RewardCatalogEntry(
        "slip",
        "penalty",
        "contact",
        -0.1,
        (
            _p("threshold", 0.25, 0.05, 0.8, 0.01),
            _p("sigma", 0.12, 0.04, 0.4),
        ),
    ),
    RewardCatalogEntry(
        "zmp",
        "penalty",
        "stability",
        -0.15,
        (
            _p("margin", 0.02, 0.005, 0.08, 0.005),
            _p("sigma", 0.03, 0.01, 0.12),
        ),
    ),
)

_CATALOG_BY_ID: dict[str, RewardCatalogEntry] = {e.id: e for e in REWARD_CATALOG}

_LEGACY_ID_MAP: dict[str, str] = {
    "lin_vel_tracking": "forward_tracking",
    "ang_vel_tracking": "yaw_tracking",
    "base_height": "height",
    "orientation_upright": "upright",
    "foot_contact": "contact",
    "velocity_penalty": "linear_velocity",
    "orientation_penalty": "posture_penalty",
    "torque_penalty": "joint_velocity",
    "gait_symmetry": "diagonal_balance",
    "action_smoothness": "smoothness",
    "impact_penalty": "stumble",
}

_STAND_ENABLE_REWARDS = frozenset(
    {"alive", "upright", "height", "posture", "contact"}
)
_STAND_ENABLE_PENALTIES = frozenset(
    {
        "linear_velocity",
        "angular_velocity",
        "z_velocity",
        "joint_velocity",
        "action_rate",
        "smoothness",
        "posture_penalty",
    }
)

_LOCO_ENABLE_REWARDS = frozenset(
    {
        "alive",
        "upright",
        "height",
        "posture",
        "contact",
        "forward_tracking",
        "forward_progress",
        "lateral_tracking",
        "yaw_tracking",
        "diagonal_balance",
        "air_time",
        "foot_clearance",
    }
)
_LOCO_ENABLE_PENALTIES = frozenset(
    {
        "angular_velocity",
        "linear_velocity",
        "z_velocity",
        "joint_velocity",
        "action_velocity",
        "action_rate",
        "posture_penalty",
        "target_posture",
        "smoothness",
        "contact_balance",
        "contact_switch",
        "target_like",
        "stumble",
        "slip",
        "zmp",
    }
)


def catalog_entry(term_id: str) -> RewardCatalogEntry | None:
    tid = _LEGACY_ID_MAP.get(term_id, term_id)
    return _CATALOG_BY_ID.get(tid)


def build_catalog_term(entry: RewardCatalogEntry, *, enabled: bool = False) -> RewardTerm:
    params = {s.key: s.recommended for s in entry.params}
    return RewardTerm(
        id=entry.id,
        type=entry.type,  # type: ignore[arg-type]
        category=entry.category,
        weight=entry.recommended_weight,
        enabled=enabled,
        params=params,
    )


def build_full_reward_catalog(*, enabled_ids: frozenset[str] | None = None) -> list[RewardTerm]:
    out: list[RewardTerm] = []
    for entry in REWARD_CATALOG:
        enabled = enabled_ids is not None and entry.id in enabled_ids
        out.append(build_catalog_term(entry, enabled=enabled))
    return out


def _clamp_param(key: str, value: float, entry: RewardCatalogEntry) -> float:
    for spec in entry.params:
        if spec.key == key:
            return max(spec.minimum, min(spec.maximum, value))
    return value


def recommend_term_params(
    term: RewardTerm,
    cmd: StageCommand,
    *,
    lin_vel_scale: float = 1.0,
) -> RewardTerm:
    entry = catalog_entry(term.id)
    if not entry:
        return term
    t = term.model_copy(deep=True)
    t.weight = entry.recommended_weight
    if term.id == "height" or (entry.id == "height"):
        t.params["target_height"] = cmd.targetBodyHeight
    if entry.id == "forward_tracking":
        # Tie sigma to the commanded speed at low targets so a slower Walk command
        # doesn't accidentally reward standing still (smaller velocity error). The
        # 0.52*v term binds only below ~0.5 m/s (e.g. 0.13 at 0.25 m/s); the
        # original decreasing schedule governs the faster gaits unchanged.
        t.params["sigma"] = max(0.12, min(0.28 - 0.04 * lin_vel_scale, 0.52 * lin_vel_scale))
    if entry.id == "air_time":
        gait_scale = max(0.5, cmd.gaitSpeedScale)
        t.params["target_air_time"] = _clamp_param(
            "target_air_time",
            0.08 + 0.03 * gait_scale,
            entry,
        )
    if entry.id == "foot_clearance":
        t.params["min_clearance"] = _clamp_param(
            "min_clearance",
            0.03 + 0.01 * lin_vel_scale,
            entry,
        )
    for spec in entry.params:
        if spec.key not in t.params:
            t.params[spec.key] = spec.recommended
        else:
            t.params[spec.key] = _clamp_param(spec.key, t.params[spec.key], entry)
    return t


def recommend_reward_terms_for_stage(
    stage_terms: list[RewardTerm],
    cmd: StageCommand,
    *,
    is_stand: bool,
    lin_vel_scale: float = 1.0,
) -> list[RewardTerm]:
    """Merge stage terms with full catalog, enable optimal subset, apply recommended params."""
    merged = merge_reward_terms(stage_terms)
    enable_rewards = _STAND_ENABLE_REWARDS if is_stand else _LOCO_ENABLE_REWARDS
    enable_penalties = _STAND_ENABLE_PENALTIES if is_stand else _LOCO_ENABLE_PENALTIES
    out: list[RewardTerm] = []
    for term in merged:
        t = term.model_copy(deep=True)
        if t.type == "reward":
            t.enabled = t.id in enable_rewards
        else:
            t.enabled = t.id in enable_penalties
        if is_stand and t.id == "lateral_tracking":
            t.enabled = cmd.targetLinVelY != 0
        if t.id == "yaw_tracking" and cmd.targetAngVelZ == 0 and not is_stand:
            t.enabled = False
        if t.id == "linear_velocity" and not is_stand and lin_vel_scale > 0.2:
            t.enabled = False
        t = recommend_term_params(t, cmd, lin_vel_scale=lin_vel_scale)
        # Lower the standing-still reward floor for locomotion stages so the
        # velocity reward dominates. These terms (shared with Stand) keep their
        # full weight there — only commanded-motion stages are scaled.
        if not is_stand and t.id in ("upright", "height", "posture"):
            t.weight = round(t.weight * 0.85, 4)
        # The flat alive bonus is the other earnable-while-standing reward; trim it on
        # commanded-motion stages so "stay upright in place" doesn't out-earn the cost
        # of attempting to walk — but keep enough that a long stable episode beats a
        # short forward lunge that falls. (Relaxed 0.4 -> 0.8 after the lunge-and-fall
        # failure; forward_progress already removes the zero-velocity plateau.)
        if not is_stand and t.id == "alive":
            t.weight = round(t.weight * 0.8, 4)
        out.append(t)
    return out


def merge_reward_terms(existing: list[RewardTerm] | None) -> list[RewardTerm]:
    """Ensure every catalog term exists; map legacy ids to the new catalog."""
    by_id: dict[str, RewardTerm] = {}
    for term in existing or []:
        mapped = _LEGACY_ID_MAP.get(term.id, term.id)
        entry = catalog_entry(mapped)
        if not entry:
            continue
        t = term.model_copy(deep=True)
        t.id = entry.id
        t.type = entry.type  # type: ignore[assignment]
        t.category = entry.category
        for spec in entry.params:
            if spec.key not in t.params:
                t.params[spec.key] = spec.recommended
        by_id[entry.id] = t
    out: list[RewardTerm] = []
    for entry in REWARD_CATALOG:
        if entry.id in by_id:
            out.append(by_id[entry.id])
        else:
            out.append(build_catalog_term(entry, enabled=False))
    return out


def stand_reward_terms(cmd: StageCommand | None = None) -> list[RewardTerm]:
    terms = build_full_reward_catalog()
    command = cmd or StageCommand()
    return recommend_reward_terms_for_stage(terms, command, is_stand=True, lin_vel_scale=0.0)


def locomotion_reward_terms(
    lin_x: float,
    ang_z: float = 0.0,
    cmd: StageCommand | None = None,
) -> list[RewardTerm]:
    command = cmd or StageCommand(
        targetLinVelX=lin_x,
        targetLinVelY=0.0,
        targetAngVelZ=ang_z,
        targetBodyHeight=PLACEHOLDER_BODY_HEIGHT_M,  # placeholder; sync from geo spawn height_policy
        gaitSpeedScale=1.0,
    )
    terms = build_full_reward_catalog()
    return recommend_reward_terms_for_stage(
        terms,
        command,
        is_stand=False,
        lin_vel_scale=abs(lin_x),
    )


def list_catalog_export() -> list[dict]:
    rows: list[dict] = []
    for entry in REWARD_CATALOG:
        rows.append(
            {
                "id": entry.id,
                "type": entry.type,
                "category": entry.category,
                "recommendedWeight": entry.recommended_weight,
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
