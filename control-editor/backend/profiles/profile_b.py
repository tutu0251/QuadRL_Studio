"""ProfileB — placeholder (not implemented)."""
from __future__ import annotations

from domain.models import ControlModel


def apply_profile_b(model: ControlModel) -> ControlModel:
    for j in model.actuatedJoints:
        j.enabled = False
        j.profileParams = {"status": "not_implemented", "profile": "ProfileB"}
    model.metadata["profileB"] = "placeholder"
    return model
