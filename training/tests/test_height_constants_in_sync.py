"""Guard against drift between the three copies of standing_heights.py.

The height-policy constants are duplicated across three independently deployable
subprojects (training, rl-trainer-editor, geometry-editor) that don't import each
other. Nothing at runtime keeps them in sync, so a change to one (e.g.
PLACEHOLDER_BODY_HEIGHT_M) must be mirrored in the others. This test fails loudly
if any of them diverge.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COPIES = {
    "training": _REPO_ROOT / "training" / "quadrl_env" / "standing_heights.py",
    "rl_trainer": _REPO_ROOT / "rl-trainer-editor" / "backend" / "planner" / "standing_heights.py",
    "geometry": _REPO_ROOT / "geometry-editor" / "backend" / "domain" / "standing_heights.py",
}
# Constants that must be identical across all copies.
_SHARED_CONSTANTS = ("HEIGHT_REFERENCE", "FALL_DROP_MARGIN_M", "PLACEHOLDER_BODY_HEIGHT_M")


def _load(name: str, path: Path):
    assert path.exists(), f"missing standing_heights copy: {path}"
    spec = importlib.util.spec_from_file_location(f"_standing_heights_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # @dataclass needs the module registered during exec
    spec.loader.exec_module(mod)
    return mod


def _all_loaded():
    return {name: _load(name, path) for name, path in _COPIES.items()}


def test_shared_height_constants_match_across_copies():
    mods = _all_loaded()
    ref_name, ref_mod = next(iter(mods.items()))
    for const in _SHARED_CONSTANTS:
        ref_val = getattr(ref_mod, const)
        for name, mod in mods.items():
            val = getattr(mod, const)
            assert val == ref_val, (
                f"{const} differs between standing_heights copies: "
                f"{name}={val!r} vs {ref_name}={ref_val!r}. Keep all three in sync."
            )


def test_fall_threshold_formula_matches_across_copies():
    mods = _all_loaded()
    for target in (0.2933, 0.35, 0.5):
        vals = {name: mod.fall_threshold_for_target(target) for name, mod in mods.items()}
        assert len(set(vals.values())) == 1, f"fall_threshold_for_target({target}) diverged: {vals}"
