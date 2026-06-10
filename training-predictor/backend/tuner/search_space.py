"""The numeric search space Optuna samples — and the surface Claude re-centers.

A ``SearchSpace`` is a mutable registry of :class:`ParamSpec`. It is built from a
project's base config (so reward-weight specs match the *enabled* terms), sampled per
trial, and edited at runtime by the advisor (re-center / narrow / pin bounds). Param
names follow the ``hp.* / rw.* / rp.*.*`` convention used by :mod:`config_io`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Default PPO-hyperparameter search bounds (sane ranges for SB3 PPO locomotion).
_HP_DEFAULTS: list[dict[str, Any]] = [
    {"name": "hp.learning_rate", "kind": "float", "low": 1e-5, "high": 1e-3, "log": True},
    {"name": "hp.ent_coef", "kind": "float", "low": 1e-4, "high": 5e-2, "log": True},
    {"name": "hp.clip_range", "kind": "float", "low": 0.1, "high": 0.4, "log": False},
    {"name": "hp.gamma", "kind": "float", "low": 0.95, "high": 0.999, "log": False},
    {"name": "hp.gae_lambda", "kind": "float", "low": 0.9, "high": 0.99, "log": False},
    {"name": "hp.vf_coef", "kind": "float", "low": 0.3, "high": 1.0, "log": False},
    {"name": "hp.n_epochs", "kind": "int", "low": 5, "high": 20, "log": False},
    {"name": "hp.batch_size", "kind": "categorical", "choices": [32, 64, 128, 256]},
    {"name": "hp.n_steps", "kind": "categorical", "choices": [1024, 2048, 4096]},
]


@dataclass
class ParamSpec:
    name: str
    group: str                       # hyperparam | reward_weight | reward_param
    kind: str                        # float | int | categorical
    low: Optional[float] = None
    high: Optional[float] = None
    log: bool = False
    choices: Optional[list] = None
    fixed: Optional[Any] = None      # when set, the value is pinned (no exploration)

    def suggest(self, trial) -> Any:
        if self.fixed is not None:
            return trial.suggest_categorical(self.name, [self.fixed])
        if self.kind == "categorical":
            return trial.suggest_categorical(self.name, self.choices)
        if self.kind == "int":
            return trial.suggest_int(self.name, int(self.low), int(self.high))
        return trial.suggest_float(self.name, float(self.low), float(self.high), log=self.log)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "group": self.group, "kind": self.kind,
            "low": self.low, "high": self.high, "log": self.log,
            "choices": self.choices, "fixed": self.fixed,
        }


class SearchSpace:
    def __init__(self, specs: list[ParamSpec]):
        self._specs: dict[str, ParamSpec] = {s.name: s for s in specs}

    # ---- construction ----
    @classmethod
    def from_base(
        cls,
        reward_terms: list[dict[str, Any]],
        *,
        include_hyperparams: bool = True,
        include_reward_weights: bool = True,
        include_reward_params: bool = True,
    ) -> "SearchSpace":
        specs: list[ParamSpec] = []
        if include_hyperparams:
            for d in _HP_DEFAULTS:
                specs.append(ParamSpec(group="hyperparam", **d))
        for term in reward_terms:
            if not term.get("enabled", True):
                continue
            tid = term.get("id")
            base_w = abs(float(term.get("weight", 0.0)))
            if include_reward_weights:
                high = max(base_w * 2.0, 0.01)          # explore 0 … 2× the current magnitude
                specs.append(ParamSpec(f"rw.{tid}", "reward_weight", "float",
                                       low=0.0, high=round(high, 6), log=False))
            if include_reward_params:
                sigma = (term.get("params") or {}).get("sigma")
                if isinstance(sigma, (int, float)) and sigma > 0:
                    specs.append(ParamSpec(
                        f"rp.{tid}.sigma", "reward_param", "float",
                        low=round(max(0.02, float(sigma) * 0.4), 6),
                        high=round(float(sigma) * 2.5, 6), log=False))
        return cls(specs)

    # ---- sampling ----
    def sample(self, trial) -> dict[str, Any]:
        return {name: spec.suggest(trial) for name, spec in self._specs.items()}

    # ---- advisor edits ----
    def recenter(self, name: str, value: float, band: float = 0.5) -> Optional[dict]:
        """Shift a spec's bounds to straddle ``value`` (±band fraction), keeping the kind."""
        spec = self._specs.get(name)
        if spec is None or spec.kind == "categorical":
            return None
        before = spec.to_dict()
        v = abs(float(value))
        lo = max(0.0, v * (1.0 - band))
        hi = max(v * (1.0 + band), lo + 1e-6)
        spec.low, spec.high, spec.fixed = round(lo, 6), round(hi, 6), None
        return {"name": name, "before": before, "after": spec.to_dict()}

    def edit(self, name: str, *, low=None, high=None, log=None, fix=None) -> Optional[dict]:
        spec = self._specs.get(name)
        if spec is None:
            return None
        before = spec.to_dict()
        if fix is not None:
            spec.fixed = fix
        else:
            if low is not None:
                spec.low = float(low)
            if high is not None:
                spec.high = float(high)
            if log is not None:
                spec.log = bool(log)
        return {"name": name, "before": before, "after": spec.to_dict()}

    # ---- introspection ----
    def names(self) -> list[str]:
        return list(self._specs.keys())

    def snapshot(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._specs.values()]
