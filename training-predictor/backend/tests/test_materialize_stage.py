import pytest

from tuner import config_io


def _cur_base():
    rl = {
        "ppo_config_file": "ppo_x.yaml",
        "task": {"reward_terms": [{"id": "global_t", "type": "reward", "weight": 1.0, "enabled": True}]},
        "curriculum": {
            "enabled": True,
            "stages": [
                {"id": "stand", "name": "Stand", "order": 0, "timesteps": 400_000,
                 "reward_terms": [{"id": "upright", "type": "reward", "weight": 0.9, "enabled": True,
                                   "params": {"sigma": 0.1}}]},
                {"id": "walk", "name": "Walk", "order": 1, "timesteps": 600_000,
                 "reward_terms": [
                     {"id": "upright", "type": "reward", "weight": 0.8, "enabled": True, "params": {"sigma": 0.12}},
                     {"id": "jv", "type": "penalty", "weight": -0.001, "enabled": True, "params": {}}]},
            ],
        },
    }
    ppo = {"hyperparameters": {"learning_rate": 3e-4, "n_steps": 2048}, "parallel": {"num_envs": 1}, "device": "cpu"}
    return rl, ppo


def test_truncates_to_stage_and_writes_target_stage_only():
    rl, ppo = _cur_base()
    cfg = config_io.materialize_stage(
        rl, ppo, {"rw.upright": 1.2, "rp.upright.sigma": 0.2, "rw.jv": 0.005},
        stage_index=1, budget=20_000)

    stages = cfg["curriculum"]["stages"]
    assert [s["id"] for s in stages] == ["stand", "walk"]      # curriculum truncated to 0..1
    walk = {t["id"]: t for t in stages[1]["reward_terms"]}
    assert walk["upright"]["weight"] == 1.2                    # written into THIS stage
    assert walk["upright"]["params"]["sigma"] == 0.2
    assert walk["jv"]["weight"] == -0.005                      # penalty sign preserved
    assert stages[1]["timesteps"] == 20_000                    # stage budget set
    # earlier stage's own reward_terms untouched
    assert {t["id"]: t for t in stages[0]["reward_terms"]}["upright"]["weight"] == 0.9
    assert "ppo_config_file" not in cfg                        # pointer dropped
    assert cfg["hyperparameters"]["learning_rate"] == 3e-4     # hp kept from base


def test_stage0_truncates_to_single_stage():
    rl, ppo = _cur_base()
    cfg = config_io.materialize_stage(rl, ppo, {"rw.upright": 0.5}, stage_index=0, budget=10_000)
    stages = cfg["curriculum"]["stages"]
    assert [s["id"] for s in stages] == ["stand"]
    assert {t["id"]: t for t in stages[0]["reward_terms"]}["upright"]["weight"] == 0.5


def test_out_of_range_and_no_curriculum_raise():
    rl, ppo = _cur_base()
    with pytest.raises(ValueError):
        config_io.materialize_stage(rl, ppo, {}, stage_index=5, budget=1)
    with pytest.raises(ValueError):
        config_io.materialize_stage({"task": {}}, ppo, {}, stage_index=0, budget=1)


def test_does_not_mutate_base():
    rl, ppo = _cur_base()
    config_io.materialize_stage(rl, ppo, {"rw.upright": 9.9}, stage_index=1, budget=1)
    walk = rl["curriculum"]["stages"][1]
    assert {t["id"]: t for t in walk["reward_terms"]}["upright"]["weight"] == 0.8
    assert "ppo_config_file" in rl
