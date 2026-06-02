"""Policy observation vector dimension helpers (matches quadrl_env.observations)."""
from __future__ import annotations

from typing import Any

from domain.models import ObservationTerm


def field_dim(kind: str, field: str) -> int:
    k = (kind or "").lower()
    if k == "contact":
        return 1
    if k == "odom":
        return 1
    if k == "lidar":
        return 16 if field == "ranges" else 1
    return 3


def term_dim(term: ObservationTerm | dict[str, Any], *, n_joints: int) -> int:
    n = max(1, n_joints)
    if isinstance(term, ObservationTerm):
        tid = term.id
        source = term.source
        kind = (term.kind or "").lower()
        fields = list(term.fields or [])
    else:
        tid = str(term.get("id", ""))
        source = term.get("source", "")
        kind = str(term.get("kind") or "").lower()
        fields = list(term.get("fields") or [])

    if source == "procedural":
        if tid in ("joint_positions", "joint_velocities", "last_actions"):
            return n
        if tid == "commands":
            return 5
        if tid in ("base_lin_vel", "base_ang_vel", "projected_gravity"):
            return 3
        return 1

    if kind == "contact":
        return max(1, len(fields) or 1)
    if kind == "lidar":
        return 16
    if kind == "odom":
        return max(1, len(fields) or 1)
    if not fields:
        return 3
    return max(3, sum(field_dim(kind, f) for f in fields))


def vector_breakdown(
    terms: list[ObservationTerm],
    *,
    n_joints: int,
) -> dict[str, Any]:
    category_dims: dict[str, int] = {"state": 0, "command": 0, "sensor": 0}
    segments: list[dict[str, Any]] = []
    offset = 0
    total = 0
    enabled_count = 0
    available_count = sum(1 for t in terms if t.available)

    for term in terms:
        dim = term_dim(term, n_joints=n_joints)
        in_vector = term.enabled and term.available
        start = offset if in_vector else None
        if in_vector:
            offset += dim
            total += dim
            enabled_count += 1
            cat = term.category or "sensor"
            category_dims[cat] = category_dims.get(cat, 0) + dim
        segments.append(
            {
                "termId": term.id,
                "label": term.label or term.key,
                "category": term.category or "sensor",
                "source": term.source,
                "kind": term.kind,
                "dim": dim,
                "enabled": term.enabled,
                "available": term.available,
                "startIndex": start,
            }
        )

    return {
        "nJoints": n_joints,
        "totalDim": total,
        "enabledTermCount": enabled_count,
        "availableTermCount": available_count,
        "categoryDims": category_dims,
        "segments": segments,
    }
