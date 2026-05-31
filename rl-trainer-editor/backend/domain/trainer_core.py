"""RL trainer session logic."""
from __future__ import annotations

from domain.models import RlTrainerModel, RlTrainerPatch
from planner.curriculum import (
    apply_curriculum_first_stage,
    curriculum_total_timesteps,
    get_curriculum_template,
)
from planner.presets import apply_preset_to_model, get_preset
from profiler.machine_profiler import profile_machine
from storage import project_storage


class TrainerCore:
    def __init__(self, model: RlTrainerModel):
        self._model = model

    def get_model(self) -> RlTrainerModel:
        return self._model

    def refresh_machine_profile(self) -> RlTrainerModel:
        self._model.machineProfile = profile_machine()
        return self._model

    def apply_preset(self, preset_id: str) -> RlTrainerModel:
        apply_preset_to_model(self._model, preset_id)
        self._model.recommendationNotes.append(f"Applied preset: {get_preset(preset_id).name}.")
        return self._model

    def patch(self, body: RlTrainerPatch) -> RlTrainerModel:
        data = body.model_dump(exclude_unset=True)
        if "rewardTerms" in data:
            self._model.rewardTerms = data.pop("rewardTerms")
        if "termination" in data:
            self._model.termination = data.pop("termination")
        if "customParams" in data:
            self._model.customParams = data.pop("customParams")
        if "selectedPresetId" in data:
            self._model.selectedPresetId = data.pop("selectedPresetId")
        if "curriculum" in data:
            self._model.curriculum = data.pop("curriculum")
        return self._model

    def apply_curriculum(self, curriculum_id: str) -> RlTrainerModel:
        config = get_curriculum_template(curriculum_id)
        self._model.curriculum = config
        apply_curriculum_first_stage(self._model, config)
        total = curriculum_total_timesteps(config)
        self._model.recommendationNotes.append(
            f"Applied curriculum '{config.name}' ({len(config.stages)} stages, {total:,} steps)."
        )
        return self._model

    def set_curriculum_stage(self, stage_index: int) -> RlTrainerModel:
        stages = sorted(self._model.curriculum.stages, key=lambda s: s.order)
        if not stages or stage_index < 0 or stage_index >= len(stages):
            return self._model
        stage = stages[stage_index]
        self._model.curriculum.currentStageIndex = stage_index
        self._model.rewardTerms = [t.model_copy(deep=True) for t in stage.rewardTerms]
        self._model.termination = stage.termination.model_copy(deep=True)
        return self._model

    @staticmethod
    def bootstrap_project(name: str) -> RlTrainerModel:
        robot = project_storage.load_robot_name(name) or name
        model = RlTrainerModel(projectName=name, robotName=robot)
        core = TrainerCore(model)
        core.apply_preset("velocity_tracking")
        core.refresh_machine_profile()
        return core.get_model()
