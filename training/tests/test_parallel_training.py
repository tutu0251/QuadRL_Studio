"""Tests for parallel training wiring: per-env DDS domain isolation + scoped cleanup."""
from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quadrl_env import env_factory as ef
from quadrl_env import gazebo_cleanup as gc

_TRAIN_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_rl_train.py"
_spec = importlib.util.spec_from_file_location("run_rl_train", _TRAIN_SCRIPT)
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)


# --- base DDS domain selection --------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_domain_cache():
    """The base domain is resolved once per run and cached; reset it between tests."""
    rt._resolved_base_domain_id = None
    yield
    rt._resolved_base_domain_id = None


def test_base_domain_defaults_to_zero_when_unset() -> None:
    with patch.dict(os.environ, {}, clear=False), patch.object(
        rt, "_occupied_ros_domains", return_value=set()
    ):
        os.environ.pop("ROS_DOMAIN_ID", None)
        assert rt._base_ros_domain_id(4) == 0


def test_base_domain_respects_existing_env() -> None:
    with patch.dict(os.environ, {"ROS_DOMAIN_ID": "20"}), patch.object(
        rt, "_occupied_ros_domains", return_value=set()
    ):
        assert rt._base_ros_domain_id(4) == 20


def test_base_domain_falls_back_when_range_overflows() -> None:
    # base + num_envs must stay within the ROS_LOCALHOST_ONLY safe range; the requested
    # base 100 cannot fit num_envs=8 (would reach 108), so the lowest free block (0) wins.
    with patch.dict(os.environ, {"ROS_DOMAIN_ID": "100"}), patch.object(
        rt, "_occupied_ros_domains", return_value=set()
    ):
        assert rt._base_ros_domain_id(8) == 0


def test_base_domain_shifts_off_occupied_block_when_unset() -> None:
    # Another run already holds domains {0,1}; a fresh run (no ROS_DOMAIN_ID) must step to
    # the first block of size num_envs+1 (train + eval) that is entirely free.
    with patch.dict(os.environ, {}, clear=False), patch.object(
        rt, "_occupied_ros_domains", return_value={0, 1}
    ):
        os.environ.pop("ROS_DOMAIN_ID", None)
        # num_envs=4 -> needs domains base..base+4; base=2 gives {2,3,4,5,6}, all free.
        assert rt._base_ros_domain_id(4) == 2


def test_base_domain_explicit_request_shifts_when_block_occupied() -> None:
    # Explicit base 0 requested, but domain 2 (inside its 0..4 block) is in use: the guard
    # honours the request only if free, otherwise shifts to the lowest free block.
    with patch.dict(os.environ, {"ROS_DOMAIN_ID": "0"}), patch.object(
        rt, "_occupied_ros_domains", return_value={2}
    ):
        # base=0 blocked (contains 2); base=3 gives {3,4,5,6,7}, all free.
        assert rt._base_ros_domain_id(4) == 3


def test_base_domain_is_cached_across_calls() -> None:
    # Resolved once: a later call must not re-scan and drift, even if occupancy changes
    # (curriculum stages reuse the prior stage's still-running Gazebo servers).
    with patch.dict(os.environ, {}, clear=False), patch.object(
        rt, "_occupied_ros_domains", return_value=set()
    ):
        os.environ.pop("ROS_DOMAIN_ID", None)
        first = rt._base_ros_domain_id(4)
    with patch.object(rt, "_occupied_ros_domains", return_value={first}) as scan:
        second = rt._base_ros_domain_id(4)
    assert second == first
    scan.assert_not_called()


def test_free_domain_block_leaves_room_for_eval_domain() -> None:
    # The block reserves num_envs train domains PLUS one eval domain (base+num_envs).
    occupied = {6}  # eval domain for base=2, num_envs=4
    assert rt._free_domain_block(4, occupied, preferred=2) != 2


def test_make_vec_env_uses_subproc_for_parallel() -> None:
    with (
        patch.object(rt, "_log"),
        patch("quadrl_env.env_factory.resolve_sim_backend", return_value="ros"),
        patch("quadrl_env.env_factory.make_vec_env_fn", return_value=lambda: MagicMock()),
    ):
        import stable_baselines3.common.vec_env as ve

        with (
            patch.object(ve, "SubprocVecEnv") as subproc,
            patch.object(ve, "DummyVecEnv") as dummy,
            patch.object(ve, "VecMonitor", side_effect=lambda v: v),
        ):
            rt._make_vec_env(Path("/tmp/p"), {}, None, 3, base_domain_id=0)

        subproc.assert_called_once()
        assert subproc.call_args.kwargs.get("start_method") == "spawn"
        dummy.assert_not_called()


def test_make_vec_env_uses_dummy_for_single_env() -> None:
    with (
        patch.object(rt, "_log"),
        patch("quadrl_env.env_factory.resolve_sim_backend", return_value="ros"),
        patch("quadrl_env.env_factory.make_vec_env_fn", return_value=lambda: MagicMock()),
    ):
        import stable_baselines3.common.vec_env as ve

        with (
            patch.object(ve, "SubprocVecEnv") as subproc,
            patch.object(ve, "DummyVecEnv") as dummy,
            patch.object(ve, "VecMonitor", side_effect=lambda v: v),
        ):
            rt._make_vec_env(Path("/tmp/p"), {}, None, 1, base_domain_id=0)

        dummy.assert_called_once()
        subproc.assert_not_called()


# --- per-env ROS_DOMAIN_ID set inside the env_fn (runs in the subprocess) -------


def test_make_vec_env_fn_sets_domain_id_before_env_construction() -> None:
    seen: dict[str, str | None] = {}

    def _fake_make_env(project_dir, config, *, stage=None, env_id=0):
        seen["domain"] = os.environ.get("ROS_DOMAIN_ID")
        seen["ign_partition"] = os.environ.get("IGN_PARTITION")
        seen["gz_partition"] = os.environ.get("GZ_PARTITION")
        seen["ign_log_path"] = os.environ.get("IGN_LOG_PATH")
        seen["env_id"] = env_id
        return MagicMock()

    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        fn = ef.make_vec_env_fn(proj, {}, env_id=3, ros_domain_id=7)
        with patch.object(ef, "make_quadruped_env", _fake_make_env), patch.dict(
            os.environ, {}, clear=False
        ):
            os.environ.pop("ROS_DOMAIN_ID", None)
            fn()

        assert seen["domain"] == "7"
        # gz-transport has its own graph; ROS_DOMAIN_ID does not isolate it.
        assert seen["ign_partition"] == "quadrl_7"
        assert seen["gz_partition"] == "quadrl_7"
        # Per-env log dir, created on the project so concurrent servers don't share it.
        expected_log = proj / "gazebo_logs" / "quadrl_7"
        assert seen["ign_log_path"] == str(expected_log)
        assert expected_log.is_dir()
        assert seen["env_id"] == 3


def test_make_vec_env_fn_leaves_domain_unset_when_not_parallel() -> None:
    seen: dict[str, str | None] = {}

    def _fake_make_env(project_dir, config, *, stage=None, env_id=0):
        seen["domain"] = os.environ.get("ROS_DOMAIN_ID", "__unset__")
        seen["ign_partition"] = os.environ.get("IGN_PARTITION", "__unset__")
        seen["ign_log_path"] = os.environ.get("IGN_LOG_PATH", "__unset__")
        return MagicMock()

    fn = ef.make_vec_env_fn(Path("/tmp/p"), {}, env_id=0, ros_domain_id=None)
    with patch.object(ef, "make_quadruped_env", _fake_make_env), patch.dict(
        os.environ, {}, clear=False
    ):
        os.environ.pop("ROS_DOMAIN_ID", None)
        os.environ.pop("IGN_PARTITION", None)
        os.environ.pop("IGN_LOG_PATH", None)
        fn()

    assert seen["domain"] == "__unset__"
    assert seen["ign_partition"] == "__unset__"
    assert seen["ign_log_path"] == "__unset__"


# --- scoped Gazebo cleanup (parallel envs must not pkill each other) -------------


def test_cleanup_scoped_terminates_group_but_skips_global_pkill() -> None:
    with (
        patch.object(gc, "terminate_process_group") as term,
        patch.object(gc, "pkill_gazebo_strays") as pkill,
    ):
        gc.cleanup_training_gazebo(4321, scoped=True)

    term.assert_called_once_with(4321)
    pkill.assert_not_called()


def test_cleanup_unscoped_runs_global_pkill() -> None:
    with (
        patch.object(gc, "terminate_process_group"),
        patch.object(gc, "pkill_gazebo_strays") as pkill,
        patch.object(gc.time, "sleep"),
    ):
        gc.cleanup_training_gazebo(4321, scoped=False)

    assert pkill.call_count == 2  # SIGTERM then SIGKILL


def test_cleanup_scoped_without_pid_is_noop() -> None:
    with (
        patch.object(gc, "terminate_process_group") as term,
        patch.object(gc, "pkill_gazebo_strays") as pkill,
    ):
        gc.cleanup_training_gazebo(scoped=True)

    term.assert_not_called()
    pkill.assert_not_called()
