from tuner import config_io


def _base():
    rl = {
        "algorithm": "PPO",
        "ppo_config_file": "ppo_x_config.yaml",
        "task": {
            "reward_terms": [
                {"id": "upright", "type": "reward", "weight": 0.8, "enabled": True, "params": {"sigma": 0.12}},
                {"id": "joint_velocity", "type": "penalty", "weight": -0.00015, "enabled": True, "params": {"sigma": 1.0}},
            ],
        },
    }
    ppo = {
        "hyperparameters": {"learning_rate": 3e-4, "n_steps": 2048, "total_timesteps": 1_000_000},
        "parallel": {"num_envs": 1},
        "device": "cpu",
    }
    return rl, ppo


def test_materialize_drops_ppo_pointer_and_inlines_hyperparams():
    rl, ppo = _base()
    sampled = {"hp.learning_rate": 1e-4, "hp.batch_size": 128,
               "rw.upright": 1.5, "rw.joint_velocity": 0.0003, "rp.upright.sigma": 0.2}
    cfg = config_io.materialize(rl, ppo, sampled, total_timesteps=25_000)

    assert "ppo_config_file" not in cfg                      # else launcher clobbers our hp
    assert cfg["hyperparameters"]["learning_rate"] == 1e-4
    assert cfg["hyperparameters"]["batch_size"] == 128
    assert cfg["hyperparameters"]["total_timesteps"] == 25_000
    assert cfg["hyperparameters"]["n_steps"] == 2048         # untouched base value preserved
    assert cfg["parallel"] == {"num_envs": 1}                # PPO block inlined
    assert cfg["device"] == "cpu"


def test_reward_weight_sign_and_params():
    rl, ppo = _base()
    sampled = {"rw.upright": 1.5, "rw.joint_velocity": 0.0003, "rp.upright.sigma": 0.2}
    cfg = config_io.materialize(rl, ppo, sampled, total_timesteps=10)
    by_id = {t["id"]: t for t in cfg["task"]["reward_terms"]}
    assert by_id["upright"]["weight"] == 1.5                  # reward stays positive
    assert by_id["joint_velocity"]["weight"] == -0.0003       # penalty stays negative
    assert by_id["upright"]["params"]["sigma"] == 0.2


def _curriculum_base():
    rl, ppo = _base()
    rl["curriculum"] = {
        "enabled": True,
        "stages": [
            {"id": "stand", "order": 0, "timesteps": 400_000},
            {"id": "walk", "order": 1, "timesteps": 600_000},
        ],
    }
    return rl, ppo


def test_curriculum_budget_scales_stages_to_total():
    rl, ppo = _curriculum_base()
    cfg = config_io.materialize(rl, ppo, {}, total_timesteps=50_000)
    stages = cfg["curriculum"]["stages"]
    # 400k:600k → 40%:60% of 50k, but floored at one rollout (n_steps*num_envs = 2048*1).
    assert [s["timesteps"] for s in stages] == [20_000, 30_000]
    assert cfg["curriculum"]["total_timesteps"] == 50_000


def test_curriculum_max_stages_truncates():
    rl, ppo = _curriculum_base()
    cfg = config_io.materialize(rl, ppo, {}, total_timesteps=40_000, max_stages=1)
    stages = cfg["curriculum"]["stages"]
    assert len(stages) == 1 and stages[0]["id"] == "stand"
    assert stages[0]["timesteps"] == 40_000


def test_non_curriculum_uses_hyperparameter_total():
    rl, ppo = _base()  # no curriculum
    cfg = config_io.materialize(rl, ppo, {}, total_timesteps=12_345)
    assert cfg["hyperparameters"]["total_timesteps"] == 12_345


def test_materialize_does_not_mutate_base():
    rl, ppo = _base()
    config_io.materialize(rl, ppo, {"rw.upright": 9.9}, total_timesteps=10)
    assert rl["task"]["reward_terms"][0]["weight"] == 0.8     # original untouched
    assert "ppo_config_file" in rl
