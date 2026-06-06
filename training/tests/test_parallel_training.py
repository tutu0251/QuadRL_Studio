"""Tests for parallel training wiring: per-env DDS domain isolation + scoped cleanup."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from quadrl_env import env_factory as ef
from quadrl_env import gazebo_cleanup as gc

_TRAIN_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_rl_train.py"
_spec = importlib.util.spec_from_file_location("run_rl_train", _TRAIN_SCRIPT)
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)


# --- base DDS domain selection --------------------------------------------------


def test_base_domain_defaults_to_zero_when_unset() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ROS_DOMAIN_ID", None)
        assert rt._base_ros_domain_id(4) == 0


def test_base_domain_respects_existing_env() -> None:
    with patch.dict(os.environ, {"ROS_DOMAIN_ID": "20"}):
        assert rt._base_ros_domain_id(4) == 20


def test_base_domain_falls_back_when_range_overflows() -> None:
    # base + num_envs must stay within the ROS_LOCALHOST_ONLY safe range.
    with patch.dict(os.environ, {"ROS_DOMAIN_ID": "100"}):
        assert rt._base_ros_domain_id(8) == 0


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
        seen["env_id"] = env_id
        return MagicMock()

    fn = ef.make_vec_env_fn(Path("/tmp/p"), {}, env_id=3, ros_domain_id=7)
    with patch.object(ef, "make_quadruped_env", _fake_make_env), patch.dict(
        os.environ, {}, clear=False
    ):
        os.environ.pop("ROS_DOMAIN_ID", None)
        fn()

    assert seen["domain"] == "7"
    assert seen["env_id"] == 3


def test_make_vec_env_fn_leaves_domain_unset_when_not_parallel() -> None:
    seen: dict[str, str | None] = {}

    def _fake_make_env(project_dir, config, *, stage=None, env_id=0):
        seen["domain"] = os.environ.get("ROS_DOMAIN_ID", "__unset__")
        return MagicMock()

    fn = ef.make_vec_env_fn(Path("/tmp/p"), {}, env_id=0, ros_domain_id=None)
    with patch.object(ef, "make_quadruped_env", _fake_make_env), patch.dict(
        os.environ, {}, clear=False
    ):
        os.environ.pop("ROS_DOMAIN_ID", None)
        fn()

    assert seen["domain"] == "__unset__"


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
