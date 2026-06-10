from tuner.search_space import SearchSpace


class FakeTrial:
    """Deterministic Optuna-trial stub: floats/ints return their low bound."""
    def __init__(self):
        self.suggested = {}

    def suggest_float(self, name, low, high, log=False):
        self.suggested[name] = low
        return low

    def suggest_int(self, name, low, high):
        self.suggested[name] = low
        return low

    def suggest_categorical(self, name, choices):
        self.suggested[name] = choices[0]
        return choices[0]


def _terms():
    return [
        {"id": "upright", "type": "reward", "weight": 0.8, "enabled": True, "params": {"sigma": 0.12}},
        {"id": "contact", "type": "reward", "weight": 0.35, "enabled": True, "params": {"min_contacts": 2.0}},
        {"id": "forward_tracking", "type": "reward", "weight": 1.0, "enabled": False, "params": {"sigma": 0.28}},
    ]


def test_from_base_builds_specs_for_enabled_terms_only():
    space = SearchSpace.from_base(_terms())
    names = set(space.names())
    assert "hp.learning_rate" in names and "hp.batch_size" in names
    assert "rw.upright" in names and "rw.contact" in names
    assert "rw.forward_tracking" not in names          # disabled term excluded
    assert "rp.upright.sigma" in names                 # term with sigma gets a param spec
    assert "rp.contact.sigma" not in names             # no sigma param → no spec


def test_sample_returns_all_params():
    space = SearchSpace.from_base(_terms())
    sampled = space.sample(FakeTrial())
    assert set(sampled.keys()) == set(space.names())
    assert sampled["rw.upright"] == 0.0                # low bound from FakeTrial
    assert sampled["hp.batch_size"] == 32              # first categorical choice


def test_recenter_shifts_bounds():
    space = SearchSpace.from_base(_terms())
    diff = space.recenter("rw.upright", 1.2)
    assert diff is not None
    snap = {s["name"]: s for s in space.snapshot()}
    spec = snap["rw.upright"]
    assert spec["low"] < 1.2 < spec["high"]            # bounds straddle the new center


def test_edit_can_pin_and_set_bounds():
    space = SearchSpace.from_base(_terms())
    assert space.edit("hp.learning_rate", low=1e-4, high=5e-4) is not None
    snap = {s["name"]: s for s in space.snapshot()}
    assert snap["hp.learning_rate"]["low"] == 1e-4
    assert space.edit("hp.clip_range", fix=0.2) is not None
    snap = {s["name"]: s for s in space.snapshot()}
    assert snap["hp.clip_range"]["fixed"] == 0.2
    assert space.edit("does.not.exist", low=1) is None
