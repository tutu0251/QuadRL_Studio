"""Tests for training launcher paths."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.train_manager import _REPO_ROOT, _TRAIN_SCRIPT


def test_train_script_exists():
    assert _TRAIN_SCRIPT.is_file()
    assert (_REPO_ROOT / "training" / "scripts" / "run_rl_train.py").is_file()
