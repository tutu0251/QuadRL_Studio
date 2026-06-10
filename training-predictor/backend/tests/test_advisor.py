import json

import optuna

from tuner import advisor as advisor_mod
from tuner import study as study_mod
from tuner.search_space import SearchSpace


class FakeTrial:
    def __init__(self, number, value, params):
        self.number = number
        self.value = value
        self.params = params
        self.state = optuna.trial.TrialState.COMPLETE


class FakeStudy:
    def __init__(self, trials):
        self.trials = trials


def test_summarize_ranks_and_collects_ranges():
    trials = [
        FakeTrial(0, 1.0, {"hp.learning_rate": 1e-4, "rw.upright": 0.5}),
        FakeTrial(1, 3.0, {"hp.learning_rate": 3e-4, "rw.upright": 0.9}),
        FakeTrial(2, 2.0, {"hp.learning_rate": 5e-4, "rw.upright": 1.2}),
    ]
    space = SearchSpace.from_base(
        [{"id": "upright", "type": "reward", "weight": 0.8, "enabled": True, "params": {"sigma": 0.12}}])
    s = advisor_mod.summarize(FakeStudy(trials), space)
    assert s["n_completed"] == 3
    assert s["best"]["number"] == 1 and s["best"]["value"] == 3.0
    assert s["top_trials"][0]["number"] == 1
    assert s["explored_ranges"]["rw.upright"] == {"min": 0.5, "max": 1.2}
    assert any(spec["name"] == "rw.upright" for spec in s["current_search_space"])


def test_decision_schema_shape():
    schema = advisor_mod.DECISION_SCHEMA
    assert schema["additionalProperties"] is False
    for key in ("action", "stop", "rationale",
                "reward_weight_overrides", "reward_param_overrides", "search_space_overrides"):
        assert key in schema["required"] and key in schema["properties"]
    item = schema["properties"]["search_space_overrides"]["items"]
    assert set(item["required"]) == {"name", "low", "high", "log", "fix"}


def test_api_advisor_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    adv = advisor_mod.ClaudeApiAdvisor()
    assert adv.available is False
    assert adv.advise(FakeStudy([]), SearchSpace.from_base([])) is None


def test_extract_json_handles_fences_and_prose():
    fenced = "Here is my decision:\n```json\n{\"action\": \"continue\", \"stop\": false}\n```\n"
    assert advisor_mod._extract_json(fenced) == {"action": "continue", "stop": False}
    raw = '{"action": "stop", "stop": true}'
    assert advisor_mod._extract_json(raw)["stop"] is True


def test_make_advisor_auto_prefers_api_then_cli(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("QUADRL_ADVISOR_BACKEND", raising=False)
    assert advisor_mod.make_advisor().backend == "api"

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(advisor_mod, "find_claude_cli", lambda: "/usr/bin/claude")
    assert advisor_mod.make_advisor().backend == "claude_cli"

    monkeypatch.setattr(advisor_mod, "find_claude_cli", lambda: None)
    assert advisor_mod.make_advisor().available is False  # disabled, pure Optuna


def test_cli_advisor_parses_envelope(monkeypatch):
    monkeypatch.setattr(advisor_mod, "find_claude_cli", lambda: "/usr/bin/claude")
    adv = advisor_mod.ClaudeCliAdvisor()
    assert adv.available and adv.backend == "claude_cli"

    decision = {"action": "continue", "stop": False, "rationale": "ok",
                "reward_weight_overrides": [], "reward_param_overrides": [],
                "search_space_overrides": []}
    envelope = json.dumps({"type": "result", "is_error": False, "result": json.dumps(decision)})

    class FakeProc:
        returncode = 0
        stdout = envelope
        stderr = ""

    monkeypatch.setattr(advisor_mod.subprocess, "run", lambda *a, **k: FakeProc())
    space = SearchSpace.from_base([])
    out = adv.advise(FakeStudy([FakeTrial(0, 1.0, {})]), space)
    assert out == decision


def test_apply_decision_recenters_and_edits():
    space = SearchSpace.from_base(
        [{"id": "upright", "type": "reward", "weight": 0.8, "enabled": True, "params": {"sigma": 0.12}}])
    decision = {
        "action": "adjust_reward_weights",
        "stop": False,
        "rationale": "upright too low; raise it",
        "reward_weight_overrides": [{"id": "upright", "value": 1.4}],
        "reward_param_overrides": [{"id": "upright", "param": "sigma", "value": 0.18}],
        "search_space_overrides": [{"name": "hp.learning_rate", "low": 1e-4, "high": 4e-4, "log": True, "fix": None}],
    }
    logs = []
    applied = study_mod.apply_decision(space, decision, lambda lvl, msg: logs.append(msg))
    assert applied["action"] == "adjust_reward_weights"
    names_changed = {c["name"] for c in applied["changes"]}
    assert {"rw.upright", "rp.upright.sigma", "hp.learning_rate"} <= names_changed
    snap = {s["name"]: s for s in space.snapshot()}
    assert snap["rw.upright"]["low"] < 1.4 < snap["rw.upright"]["high"]
    assert snap["hp.learning_rate"]["low"] == 1e-4
