import yaml

from tuner import config_writer, paths


def _make_project(root, name="p"):
    exports = root / name / "exports"
    exports.mkdir(parents=True)
    rl = {
        "ppo_config_file": f"ppo_{name}_config.yaml",
        "task": {"reward_terms": [
            {"id": "upright", "type": "reward", "weight": 0.8, "enabled": True, "params": {"sigma": 0.12}},
            {"id": "joint_velocity", "type": "penalty", "weight": -0.00015, "enabled": True, "params": {"sigma": 1.0}},
        ]},
    }
    ppo = {"hyperparameters": {"learning_rate": 3e-4, "n_steps": 2048}}
    (exports / f"rl_{name}_config.yaml").write_text(yaml.safe_dump(rl))
    (exports / f"ppo_{name}_config.yaml").write_text(yaml.safe_dump(ppo))


def test_apply_params_writes_back_with_backups(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    _make_project(tmp_path)

    params = {"hp.learning_rate": 1e-4, "rw.upright": 1.4,
              "rw.joint_velocity": 0.0002, "rp.upright.sigma": 0.2}
    summary = config_writer.apply_params("p", params, stamp="TS")

    ppo = yaml.safe_load(paths.base_ppo_config("p").read_text())
    rl = yaml.safe_load(paths.base_rl_config("p").read_text())
    by_id = {t["id"]: t for t in rl["task"]["reward_terms"]}

    assert ppo["hyperparameters"]["learning_rate"] == 1e-4
    assert ppo["hyperparameters"]["n_steps"] == 2048          # untouched preserved
    assert by_id["upright"]["weight"] == 1.4                   # reward positive
    assert by_id["joint_velocity"]["weight"] == -0.0002        # penalty sign preserved
    assert by_id["upright"]["params"]["sigma"] == 0.2

    # backups exist for both touched files
    assert (paths.base_ppo_config("p").parent / "ppo_p_config.yaml.bak-TS").exists()
    assert (paths.base_rl_config("p").parent / "rl_p_config.yaml.bak-TS").exists()
    assert summary["hyperparameters"] == {"learning_rate": 1e-4}
    assert summary["reward_weights"] == {"upright": 1.4, "joint_velocity": -0.0002}
    assert len(summary["files"]) == 2 and len(summary["backups"]) == 2


def test_apply_params_hyperparams_fallback_to_rl_when_no_ppo(tmp_path, monkeypatch):
    monkeypatch.setenv("QUADRL_PROJECTS_DIR", str(tmp_path))
    _make_project(tmp_path, "q")
    paths.base_ppo_config("q").unlink()  # no PPO export

    config_writer.apply_params("q", {"hp.gamma": 0.97}, stamp="TS")
    rl = yaml.safe_load(paths.base_rl_config("q").read_text())
    assert rl["hyperparameters"]["gamma"] == 0.97
