"""PPO planner session logic."""
from __future__ import annotations

from domain.models import (
    ExportFormatConfig,
    OutputPatch,
    ParallelConfig,
    ParallelPatch,
    PpoParamsUpdate,
    PpoPlannerModel,
    RecommendationResponse,
    VecEnvType,
)
from planner.defaults import SB3_BASELINE
from planner.output_defaults import DEFAULT_BEST_MODEL, DEFAULT_CHECKPOINT, DEFAULT_EXPORT_FORMAT
from planner.parallel_guard import normalize_parallel_config
from planner.recommender import recommend_ppo_config
from profiler.machine_profiler import profile_machine
from storage import project_storage


def _physical_cores(model: PpoPlannerModel) -> int:
    if model.machineProfile:
        return max(1, model.machineProfile.cpuCountPhysical)
    return max(1, profile_machine().cpuCountPhysical)


class PlannerCore:
    def __init__(self, model: PpoPlannerModel):
        self._model = model

    def get_model(self) -> PpoPlannerModel:
        return self._model

    def _normalize_parallel(self) -> None:
        par, _ = normalize_parallel_config(
            self._model.parallel,
            physical_cores=_physical_cores(self._model),
        )
        self._model.parallel = par

    def apply_recommendation(self) -> RecommendationResponse:
        machine = profile_machine()
        params, parallel, notes = recommend_ppo_config(machine)
        self._model.machineProfile = machine
        self._model.recommendationNotes = notes
        if self._model.useRecommended:
            self._model.params = params
            self._model.parallel = parallel
        return RecommendationResponse(
            params=params,
            parallel=parallel,
            notes=notes,
            machine=machine,
        )

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

    def patch_parallel(self, body: ParallelPatch) -> PpoPlannerModel:
        data = body.model_dump(exclude_unset=True)
        if "useRecommended" in data:
            self._model.useRecommended = data.pop("useRecommended")
        if data:
            self._model.parallel = self._model.parallel.model_copy(
                update=data,
                deep=True,
            )
        self._normalize_parallel()
        return self._model

    def patch_output(self, body: OutputPatch) -> PpoPlannerModel:
        data = body.model_dump(exclude_unset=True)
        if ckpt := data.get("checkpoint"):
            self._model.checkpoint = self._model.checkpoint.model_copy(update=ckpt, deep=True)
        if best := data.get("bestModel"):
            self._model.bestModel = self._model.bestModel.model_copy(update=best, deep=True)
        if export_fmt := data.get("exportFormat"):
            patched = self._model.exportFormat.model_copy(update=export_fmt, deep=True)
            if "formats" in export_fmt:
                patched = patched.model_copy(
                    update={"formats": ExportFormatConfig._normalize_formats(patched.formats)}
                )
            self._model.exportFormat = patched
        return self._model

    def reset_to_baseline(self) -> PpoPlannerModel:
        self._model.params = SB3_BASELINE.model_copy(deep=True)
        self._model.parallel = ParallelConfig(
            numEnvs=1,
            vecEnvType=VecEnvType.DUMMY,
            nProc=None,
        )
        self._model.checkpoint = DEFAULT_CHECKPOINT.model_copy(deep=True)
        self._model.bestModel = DEFAULT_BEST_MODEL.model_copy(deep=True)
        self._model.exportFormat = DEFAULT_EXPORT_FORMAT.model_copy(deep=True)
        self._model.useRecommended = False
        return self._model

    @staticmethod
    def bootstrap_project(name: str) -> PpoPlannerModel:
        robot = project_storage.load_robot_name(name) or name
        model = PpoPlannerModel(projectName=name, robotName=robot)
        core = PlannerCore(model)
        core.apply_recommendation()
        return core.get_model()
