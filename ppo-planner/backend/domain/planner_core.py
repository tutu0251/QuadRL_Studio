"""PPO planner session logic."""
from __future__ import annotations

from domain.models import (
    PpoHyperparams,
    PpoParamsUpdate,
    PpoPlannerModel,
    RecommendationResponse,
)
from planner.recommender import recommend_ppo_params
from profiler.machine_profiler import profile_machine
from storage import project_storage


class PlannerCore:
    def __init__(self, model: PpoPlannerModel):
        self._model = model

    def get_model(self) -> PpoPlannerModel:
        return self._model

    def apply_recommendation(self) -> RecommendationResponse:
        machine = profile_machine()
        params, notes = recommend_ppo_params(machine)
        self._model.machineProfile = machine
        self._model.recommendationNotes = notes
        if self._model.useRecommended:
            self._model.params = params
        return RecommendationResponse(params=params, notes=notes, machine=machine)

    def refresh_machine_profile(self) -> PpoPlannerModel:
        self._model.machineProfile = profile_machine()
        return self._model

    def patch_params(self, body: PpoParamsUpdate) -> PpoPlannerModel:
        data = body.model_dump(exclude_unset=True)
        if "useRecommended" in data:
            self._model.useRecommended = data.pop("useRecommended")
        if data:
            self._model.params = self._model.params.model_copy(
                update=data,
                deep=True,
            )
        return self._model

    def reset_to_baseline(self) -> PpoPlannerModel:
        from planner.defaults import SB3_BASELINE

        self._model.params = SB3_BASELINE.model_copy(deep=True)
        self._model.useRecommended = False
        return self._model

    @staticmethod
    def bootstrap_project(name: str) -> PpoPlannerModel:
        robot = project_storage.load_robot_name(name) or name
        model = PpoPlannerModel(projectName=name, robotName=robot)
        core = PlannerCore(model)
        core.apply_recommendation()
        return core.get_model()
