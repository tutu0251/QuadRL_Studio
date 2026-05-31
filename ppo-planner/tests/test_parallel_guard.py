"""Tests for parallel config normalization and validation."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from domain.models import MachineProfile, ParallelConfig, VecEnvType
from planner.parallel_guard import (
    max_recommended_envs,
    normalize_parallel_config,
    parallel_validation_issues,
)


def test_dummy_clears_n_proc():
    par, notes = normalize_parallel_config(
        ParallelConfig(numEnvs=4, vecEnvType=VecEnvType.DUMMY, nProc=4),
        physical_cores=8,
    )
    assert par.nProc is None
    assert any("n_proc" in n for n in notes)


def test_caps_n_proc_to_num_envs():
    par, notes = normalize_parallel_config(
        ParallelConfig(numEnvs=2, vecEnvType=VecEnvType.SUBPROC, nProc=8),
        physical_cores=8,
    )
    assert par.nProc == 2
    assert any("Capped" in n for n in notes)


def test_single_env_switches_to_dummy():
    par, notes = normalize_parallel_config(
        ParallelConfig(numEnvs=1, vecEnvType=VecEnvType.SUBPROC, nProc=1),
        physical_cores=4,
    )
    assert par.vecEnvType == VecEnvType.DUMMY
    assert par.nProc is None


def test_validation_flags_n_proc_exceeds_envs():
    errors, _ = parallel_validation_issues(
        ParallelConfig(numEnvs=2, vecEnvType=VecEnvType.SUBPROC, nProc=4),
        machine=None,
        physical_cores=8,
    )
    assert any("num_envs" in e for e in errors)


def test_max_recommended_envs_scales_with_ram():
    low = max_recommended_envs(
        MachineProfile(ramGb=4.0, cpuCountPhysical=8, cpuCountLogical=16)
    )
    high = max_recommended_envs(
        MachineProfile(ramGb=64.0, cpuCountPhysical=16, cpuCountLogical=32)
    )
    assert low == 1
    assert high >= 4
