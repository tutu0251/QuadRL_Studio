"""Tests for mid-curriculum resume: mapping a checkpoint back to its stage and
reading its embedded step count so a resumed run continues the in-progress stage
instead of replaying the whole curriculum."""
from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

_TRAIN_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_rl_train.py"
_spec = importlib.util.spec_from_file_location("run_rl_train", _TRAIN_SCRIPT)
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)


CONFIG = {"checkpoint": {"filename_template": "ppo_{stage_id}"}}
STAGES = [
    {"id": "walk", "order": 0, "timesteps": 1_000_000},
    {"id": "walk_fast", "order": 1, "timesteps": 1_000_000},
    {"id": "turn", "order": 2, "timesteps": 1_000_000},
]


def _make_ckpt(tmp_path: Path, name: str, steps: int) -> Path:
    """Write a minimal SB3-style checkpoint zip with a JSON ``data`` member."""
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("data", json.dumps({"num_timesteps": steps}))
        zf.writestr("policy.pth", b"weights")
    return path


# --- _stage_index_for_checkpoint ------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("ppo_walk.zip", 0),  # final stage checkpoint
        ("ppo_walk_1200000_steps.zip", 0),  # periodic checkpoint
        ("ppo_walk_fast.zip", 1),  # prefix collision: not 'walk'
        ("ppo_walk_fast_50000_steps.zip", 1),
        ("ppo_turn.zip", 2),
        ("ppo_turn_steps.zip", None),  # malformed suffix
        ("best_model.zip", None),  # best-model copy has no stage id
        ("foreign_pretrained.zip", None),
    ],
)
def test_stage_index_for_checkpoint(filename, expected):
    assert rt._stage_index_for_checkpoint(STAGES, CONFIG, Path(filename)) == expected


# --- _checkpoint_num_timesteps --------------------------------------------------


def test_num_timesteps_reads_data_member(tmp_path):
    ckpt = _make_ckpt(tmp_path, "ppo_walk_1200000_steps.zip", 1_200_000)
    assert rt._checkpoint_num_timesteps(ckpt) == 1_200_000


def test_num_timesteps_missing_file_returns_none(tmp_path):
    assert rt._checkpoint_num_timesteps(tmp_path / "nope.zip") is None


def test_num_timesteps_bad_zip_returns_none(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    assert rt._checkpoint_num_timesteps(bad) is None


# --- the resume decision (mirrors main()'s resolution branch) --------------------


def _decide(ckpt: Path):
    """Replicate main()'s (start_i, seed, continue) resolution for a checkpoint."""
    matched = rt._stage_index_for_checkpoint(STAGES, CONFIG, ckpt)
    if matched is None:
        return (0, ckpt, False)
    budget = int(STAGES[matched]["timesteps"])
    done = rt._checkpoint_num_timesteps(ckpt)
    if done is not None and done >= budget:
        return (matched + 1, ckpt, False)
    return (matched, ckpt, True)


def test_mid_stage_resume_continues_that_stage(tmp_path):
    ckpt = _make_ckpt(tmp_path, "ppo_walk_fast_800000_steps.zip", 800_000)
    start_i, seed, cont = _decide(ckpt)
    assert (start_i, seed, cont) == (1, ckpt, True)


def test_completed_stage_advances_to_next_fresh(tmp_path):
    ckpt = _make_ckpt(tmp_path, "ppo_walk.zip", 1_000_000)
    start_i, _seed, cont = _decide(ckpt)
    assert start_i == 1 and cont is False


def test_completed_final_stage_has_nothing_left(tmp_path):
    ckpt = _make_ckpt(tmp_path, "ppo_turn.zip", 1_000_000)
    start_i, _seed, _cont = _decide(ckpt)
    assert start_i == len(STAGES)  # loop body runs nothing


def test_foreign_checkpoint_seeds_first_stage(tmp_path):
    ckpt = _make_ckpt(tmp_path, "pretrained.zip", 500_000)
    start_i, seed, cont = _decide(ckpt)
    assert (start_i, seed, cont) == (0, ckpt, False)
