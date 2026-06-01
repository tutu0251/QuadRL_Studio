"""Tests for realtime system stats sampling."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from profiler.system_stats import sample_system_stats


def test_sample_system_stats_shape():
    data = sample_system_stats()
    assert "sampledAt" in data
    assert "cpuPercent" in data
    assert 0 <= data["cpuPercent"] <= 100
    assert data["ramTotalMb"] >= 0
    assert 0 <= data["ramUsedPercent"] <= 100
