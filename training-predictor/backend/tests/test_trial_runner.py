import time

import pytest

from tuner import trial_runner


def test_mock_objective_finite_and_deterministic():
    s = {"hp.learning_rate": 3e-4, "hp.ent_coef": 1e-3, "hp.clip_range": 0.2, "rw.upright": 0.9}
    v1 = trial_runner.mock_objective(s)
    v2 = trial_runner.mock_objective(s)
    assert v1 == v2
    assert isinstance(v1, float) and v1 == v1  # not NaN
    # The toy optimum is near these values → score should beat an off-optimum point.
    off = trial_runner.mock_objective({"hp.learning_rate": 1e-2, "hp.clip_range": 0.4, "rw.upright": 0.0})
    assert v1 > off


def _write_events(logdir, tag, values):
    try:
        from tensorboard.compat.proto.event_pb2 import Event
        from tensorboard.compat.proto.summary_pb2 import Summary
        from tensorboard.summary.writer.event_file_writer import EventFileWriter
    except Exception:  # pragma: no cover
        pytest.skip("tensorboard proto/writer not available")
    w = EventFileWriter(str(logdir))
    for step, v in enumerate(values):
        summ = Summary(value=[Summary.Value(tag=tag, simple_value=float(v))])
        w.add_event(Event(wall_time=time.time(), step=step, summary=summ))
    w.close()


def test_read_objective_prefers_eval_and_returns_last(tmp_path):
    run_root = tmp_path / "runs" / "20260101_000000" / "training" / "PPO_1"
    run_root.mkdir(parents=True)
    _write_events(run_root, "rollout/ep_rew_mean", [1.0, 2.0, 3.0])
    _write_events(run_root, "eval/mean_reward", [10.0, 11.0, 12.5])

    final, series = trial_runner.read_objective(tmp_path / "runs" / "20260101_000000")
    assert final == 12.5                 # eval/mean_reward preferred, last point
    assert series[-1] == 12.5


def test_read_objective_falls_back_to_rollout(tmp_path):
    run_root = tmp_path / "runs" / "r" / "training" / "PPO_1"
    run_root.mkdir(parents=True)
    _write_events(run_root, "rollout/ep_rew_mean", [4.0, 5.0])
    final, _ = trial_runner.read_objective(tmp_path / "runs" / "r")
    assert final == 5.0


def test_read_objective_raises_without_events(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(RuntimeError):
        trial_runner.read_objective(tmp_path / "empty")


def test_resolve_run_dir_prefers_run_id(tmp_path, monkeypatch):
    import os
    project_dir = tmp_path / "proj"
    (project_dir / "runs" / "20260101_120000").mkdir(parents=True)
    (project_dir / "runs" / "20260101_130000").mkdir(parents=True)
    os.utime(project_dir / "runs" / "20260101_120000", (1000, 1000))
    os.utime(project_dir / "runs" / "20260101_130000", (2000, 2000))  # newer
    monkeypatch.setattr(trial_runner.paths, "project_dir", lambda p: project_dir)

    # explicit run_id wins
    out = trial_runner.resolve_run_dir("proj", "20260101_120000")
    assert out.name == "20260101_120000"
    # missing run_id → newest dir
    out2 = trial_runner.resolve_run_dir("proj", None)
    assert out2.name == "20260101_130000"
