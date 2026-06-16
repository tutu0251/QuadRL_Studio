"""Reading best params back from on-disk artifacts (so the page can apply after a reload/restart)."""
import json

import optuna

from tuner import paths, stage_sequence, study as study_mod


def _study_dir(tmp, project, name):
    d = paths.tuning_root(project) / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_load_best_from_db_reads_winning_trial(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    name = "study_x"
    d = _study_dir(tmp_path, "proj", name)
    s = optuna.create_study(study_name=name, storage=f"sqlite:///{d / 'optuna.db'}",
                            direction="maximize")
    s.add_trial(optuna.trial.create_trial(params={"hp.gamma": 0.9}, distributions={
        "hp.gamma": optuna.distributions.FloatDistribution(0.8, 0.99)}, value=1.0))
    s.add_trial(optuna.trial.create_trial(params={"hp.gamma": 0.95}, distributions={
        "hp.gamma": optuna.distributions.FloatDistribution(0.8, 0.99)}, value=2.0))

    best = study_mod.load_best_from_db("proj", name)
    assert best["value"] == 2.0
    assert best["params"]["hp.gamma"] == 0.95


def test_load_best_from_db_none_without_completed_trials(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    name = "study_empty"
    d = _study_dir(tmp_path, "proj", name)
    optuna.create_study(study_name=name, storage=f"sqlite:///{d / 'optuna.db'}", direction="maximize")
    assert study_mod.load_best_from_db("proj", name) is None


def test_load_decisions_replays_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    d = _study_dir(tmp_path, "proj", "study_d")
    (d / "decisions.jsonl").write_text(
        json.dumps({"action": "recenter", "after_trial": 5}) + "\n" + "  \n", encoding="utf-8")
    decisions = study_mod.load_decisions("proj", "study_d")
    assert len(decisions) == 1 and decisions[0]["after_trial"] == 5


def test_best_stage_params_from_sequence_file(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    d = _study_dir(tmp_path, "proj", "seq_y")
    (d / "sequence.json").write_text(json.dumps({
        "seq_name": "seq_y", "project": "proj",
        "stage_results": {
            "0": {"status": "done", "best_params": {"rw.upright": 1.2}},
            "1": {"status": "running", "best_params": {"rw.jv": 0.5}},  # not done → excluded
            "2": {"status": "done", "best_params": {}},                  # done but empty → excluded
        },
    }), encoding="utf-8")

    data = stage_sequence.load_sequence_file("proj", "seq_y")
    best = stage_sequence.best_stage_params_from_file(data)
    assert best == {0: {"rw.upright": 1.2}}
