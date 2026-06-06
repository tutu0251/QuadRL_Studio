"""Guard against drift between the two copies of standing_heights.py.

The height policy constants are intentionally duplicated across two independently
deployable subprojects (training/quadrl_env and rl-trainer-editor/backend/planner)
that do not import each other. Nothing at runtime keeps them in sync, so a change
to one (e.g. PLACEHOLDER_BODY_HEIGHT_M) must be mirrored in the other. This test
fails loudly if they ever diverge.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COPIES = {
    "training": _REPO_ROOT / "training" / "quadrl_env" / "standing_heights.py",
    "rl_trainer": _REPO_ROOT / "rl-trainer-editor" / "backend" / "planner" / "standing_heights.py",
}
# Constants that must be identical across both copies.
_SHARED_CONSTANTS = ("HEIGHT_REFERENCE", "FALL_DROP_MARGIN_M", "PLACEHOLDER_BODY_HEIGHT_M")


def _load(name: str, path: Path):
    assert path.exists(), f"missing standing_heights copy: {path}"
    spec = importlib.util.spec_from_file_location(f"_standing_heights_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # @dataclass needs the module registered during exec
    spec.loader.exec_module(mod)
    return mod


def test_shared_height_constants_match_across_copies():
    training = _load("training", _COPIES["training"])
    rl_trainer = _load("rl_trainer", _COPIES["rl_trainer"])
    for const in _SHARED_CONSTANTS:
        a = getattr(training, const)
        b = getattr(rl_trainer, const)
        assert a == b, (
            f"{const} differs between standing_heights copies: "
            f"training={a!r} vs rl-trainer-editor={b!r}. Keep them in sync."
        )


def test_fall_threshold_formula_matches_across_copies():
    training = _load("training", _COPIES["training"])
    rl_trainer = _load("rl_trainer", _COPIES["rl_trainer"])
    for target in (0.2933, 0.35, 0.5):
        assert training.fall_threshold_for_target(target) == rl_trainer.fall_threshold_for_target(target)
