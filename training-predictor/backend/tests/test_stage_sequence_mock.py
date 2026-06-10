import yaml

from tuner import stage_sequence


def _make_curriculum_project(tmp, name="seqproj"):
    exports = tmp / name / "exports"
    exports.mkdir(parents=True)
    rl = {"curriculum": {"enabled": True, "stages": [
        {"id": "stand", "name": "Stand", "order": 0, "timesteps": 1000,
         "reward_terms": [{"id": "upright", "type": "reward", "weight": 0.9, "enabled": True,
                           "params": {"sigma": 0.1}}]},
        {"id": "walk", "name": "Walk", "order": 1, "timesteps": 1000,
         "reward_terms": [{"id": "upright", "type": "reward", "weight": 0.8, "enabled": True,
                           "params": {"sigma": 0.12}}]},
    ]}}
    (exports / f"rl_{name}_config.yaml").write_text(yaml.safe_dump(rl))
    return name


def test_mock_sequence_runs_all_stages(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    name = _make_curriculum_project(tmp_path)
    cfg = stage_sequence.StageSeqConfig(
        project=name, stages_to_tune=[0, 1], trials_per_stage=4,
        advisor_every_n=99, mock_objective=True)
    sess = stage_sequence.StageSequenceSession(config=cfg)
    sess.run()

    assert sess.status == "complete", sess.error
    assert set(sess.stage_results) == {0, 1}
    for k in (0, 1):
        r = sess.stage_results[k]
        assert r["status"] == "done"
        assert r["best_value"] is not None
        assert "rw.upright" in r["best_params"]
        assert r["n_completed"] == 4

    seq_json = tmp_path / name / "tuning" / cfg.seq_name / "sequence.json"
    assert seq_json.is_file()

    # best_stage_params surfaces both stages for the final apply step
    bp = sess.best_stage_params()
    assert set(bp) == {0, 1}


def test_mock_sequence_resume_skips_done_stages(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    name = _make_curriculum_project(tmp_path)
    seq = "seq_fixed"

    cfg1 = stage_sequence.StageSeqConfig(
        project=name, stages_to_tune=[0, 1], trials_per_stage=3,
        advisor_every_n=99, mock_objective=True, seq_name=seq)
    stage_sequence.StageSequenceSession(config=cfg1).run()

    cfg2 = stage_sequence.StageSeqConfig(
        project=name, stages_to_tune=[0, 1], trials_per_stage=3,
        advisor_every_n=99, mock_objective=True, seq_name=seq)
    s2 = stage_sequence.StageSequenceSession(config=cfg2)
    logs: list[str] = []
    s2.log = lambda level, msg: logs.append(msg)
    s2.run()

    assert s2.status == "complete"
    assert any("already tuned" in m for m in logs)
