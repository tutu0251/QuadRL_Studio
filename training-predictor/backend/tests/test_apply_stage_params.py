import yaml

from tuner import config_io, config_writer


def _make_project(tmp, name="proj"):
    exports = tmp / name / "exports"
    exports.mkdir(parents=True)
    rl = {"curriculum": {"enabled": True, "stages": [
        {"id": "stand", "name": "Stand", "order": 0,
         "reward_terms": [{"id": "upright", "type": "reward", "weight": 0.9, "enabled": True,
                           "params": {"sigma": 0.1}}]},
        {"id": "walk", "name": "Walk", "order": 1,
         "reward_terms": [
             {"id": "upright", "type": "reward", "weight": 0.8, "enabled": True, "params": {"sigma": 0.12}},
             {"id": "jv", "type": "penalty", "weight": -0.001, "enabled": True, "params": {}}]},
    ]}}
    (exports / f"rl_{name}_config.yaml").write_text(yaml.safe_dump(rl))
    return name


def test_writes_per_stage_reward_terms_with_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    name = _make_project(tmp_path)

    summary = config_writer.apply_stage_params(
        name, {1: {"rw.upright": 1.3, "rw.jv": 0.004, "rp.upright.sigma": 0.2}})

    assert summary["files"] and summary["backups"]
    assert 1 in summary["stages"] and summary["stages"][1]["name"] == "Walk"

    rl, _ = config_io.load_base(name)
    stages = sorted(rl["curriculum"]["stages"], key=lambda s: s["order"])
    walk = {t["id"]: t for t in stages[1]["reward_terms"]}
    assert walk["upright"]["weight"] == 1.3
    assert walk["jv"]["weight"] == -0.004                       # penalty sign preserved
    assert walk["upright"]["params"]["sigma"] == 0.2
    # stage 0 untouched
    assert {t["id"]: t for t in stages[0]["reward_terms"]}["upright"]["weight"] == 0.9


def test_no_changes_when_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    name = _make_project(tmp_path)
    summary = config_writer.apply_stage_params(name, {})
    assert summary["files"] == [] and summary["backups"] == []
