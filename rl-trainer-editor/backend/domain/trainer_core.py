"""RL trainer session logic."""
from __future__ import annotations

from domain.migration import migrate_model
from domain.models import (
    CheckpointInfo,
    CurriculumConfig,
    CurriculumEntry,
    CurriculumStage,
    GaitType,
    RlTrainerModel,
    RlTrainerPatch,
    new_id,
)
from planner.curriculum_templates import (
    apply_curriculum_first_stage,
    curriculum_to_entry,
    curriculum_total_timesteps,
    get_curriculum_template,
)
from planner.gait_defaults import build_gait, default_gait_library
from planner.presets import apply_preset_to_model, get_preset
from planner.recommender import recommend_curriculum_timesteps, recommend_gait, recommend_stage_params
from profiler.machine_profiler import profile_machine
from storage import project_storage


class TrainerCore:
    def __init__(self, model: RlTrainerModel):
        self._model = migrate_model(model)

    def get_model(self) -> RlTrainerModel:
        return self._model

    def refresh_machine_profile(self) -> RlTrainerModel:
        self._model.machineProfile = profile_machine()
        return self._model

    def apply_preset(self, preset_id: str) -> RlTrainerModel:
        apply_preset_to_model(self._model, preset_id)
        self._model.recommendationNotes.append(f"Applied preset: {get_preset(preset_id).name}.")
        return self._model

    def _sync_curriculum_to_library(self) -> None:
        aid = self._model.activeCurriculumId
        if not aid:
            return
        for i, entry in enumerate(self._model.curriculumLibrary):
            if entry.id == aid:
                self._model.curriculumLibrary[i] = curriculum_to_entry(self._model.curriculum)
                self._model.curriculumLibrary[i].id = aid
                return

    def _sync_library_to_curriculum(self, entry_id: str) -> None:
        for entry in self._model.curriculumLibrary:
            if entry.id == entry_id:
                self._model.curriculum = CurriculumConfig(
                    enabled=True,
                    curriculumId=entry.id,
                    name=entry.name,
                    description=entry.description,
                    terrainProfile=entry.terrainProfile,
                    stages=[s.model_copy(deep=True) for s in entry.stages],
                    currentStageIndex=0,
                    loadPreviousCheckpoint=entry.loadPreviousCheckpoint,
                    resetPolicyOnStageAdvance=entry.resetPolicyOnStageAdvance,
                )
                self._model.activeCurriculumId = entry_id
                return

    def patch(self, body: RlTrainerPatch) -> RlTrainerModel:
        data = body.model_dump(exclude_unset=True)
        for key in (
            "rewardTerms",
            "termination",
            "customParams",
            "selectedPresetId",
            "gaitTypes",
            "curriculumLibrary",
            "activeCurriculumId",
            "trainingCheckpoint",
            "useRecommended",
        ):
            if key in data:
                setattr(self._model, key, data.pop(key))
        if "curriculum" in data:
            self._model.curriculum = data.pop("curriculum")
            self._sync_curriculum_to_library()
        if "activeCurriculumId" in body.model_dump(exclude_unset=True):
            if self._model.activeCurriculumId:
                self._sync_library_to_curriculum(self._model.activeCurriculumId)
        return self._model

    def apply_curriculum(self, curriculum_id: str) -> RlTrainerModel:
        config = get_curriculum_template(curriculum_id)
        entry = curriculum_to_entry(config)
        entry.id = curriculum_id
        self._model.curriculum = config
        self._model.activeCurriculumId = curriculum_id
        existing = {e.id: i for i, e in enumerate(self._model.curriculumLibrary)}
        if curriculum_id in existing:
            self._model.curriculumLibrary[existing[curriculum_id]] = entry
        else:
            self._model.curriculumLibrary.append(entry)
        if not self._model.gaitTypes:
            self._model.gaitTypes = default_gait_library()
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

    def add_curriculum(self, name: str, terrain: str = "flat") -> RlTrainerModel:
        entry = CurriculumEntry(
            id=new_id(),
            name=name or "New curriculum",
            description="Custom curriculum",
            terrainProfile=terrain,  # type: ignore[arg-type]
            stages=[],
        )
        self._model.curriculumLibrary.append(entry)
        self._sync_library_to_curriculum(entry.id)
        return self._model

    def delete_curriculum(self, entry_id: str) -> RlTrainerModel:
        self._model.curriculumLibrary = [
            e for e in self._model.curriculumLibrary if e.id != entry_id
        ]
        if self._model.activeCurriculumId == entry_id:
            if self._model.curriculumLibrary:
                self._sync_library_to_curriculum(self._model.curriculumLibrary[0].id)
            else:
                self._model.activeCurriculumId = None
                self._model.curriculum = CurriculumConfig()
        return self._model

    def rename_curriculum(self, entry_id: str, name: str) -> RlTrainerModel:
        for entry in self._model.curriculumLibrary:
            if entry.id == entry_id:
                entry.name = name
                if self._model.activeCurriculumId == entry_id:
                    self._model.curriculum.name = name
                break
        return self._model

    def duplicate_curriculum(self, entry_id: str) -> RlTrainerModel:
        for entry in self._model.curriculumLibrary:
            if entry.id == entry_id:
                dup = entry.model_copy(deep=True)
                dup.id = new_id()
                dup.name = f"{entry.name} (copy)"
                self._model.curriculumLibrary.append(dup)
                self._sync_library_to_curriculum(dup.id)
                break
        return self._model

    def _renormalize_orders(self, stages: list[CurriculumStage]) -> list[CurriculumStage]:
        sorted_stages = sorted(stages, key=lambda s: s.order)
        for i, s in enumerate(sorted_stages):
            s.order = i
        return sorted_stages

    def add_stage(self, after_order: int | None = None) -> RlTrainerModel:
        from planner.curriculum_templates import _locomotion_terms, _stand_terms

        stages = [s.model_copy(deep=True) for s in self._model.curriculum.stages]
        insert_at = (after_order + 1) if after_order is not None else len(stages)
        new_stage = CurriculumStage(
            id=new_id(),
            name="New stage",
            order=insert_at,
            description="",
            gaitTypeId="walk",
            rewardTerms=_locomotion_terms(0.4),
        )
        stages.insert(insert_at, new_stage)
        self._model.curriculum.stages = self._renormalize_orders(stages)
        self._sync_curriculum_to_library()
        return self._model

    def delete_stage(self, stage_id: str) -> RlTrainerModel:
        stages = [s for s in self._model.curriculum.stages if s.id != stage_id]
        self._model.curriculum.stages = self._renormalize_orders(stages)
        self._sync_curriculum_to_library()
        return self._model

    def duplicate_stage(self, stage_id: str) -> RlTrainerModel:
        stages = [s.model_copy(deep=True) for s in self._model.curriculum.stages]
        for i, s in enumerate(stages):
            if s.id == stage_id:
                dup = s.model_copy(deep=True)
                dup.id = new_id()
                dup.name = f"{s.name} (copy)"
                stages.insert(i + 1, dup)
                break
        self._model.curriculum.stages = self._renormalize_orders(stages)
        self._sync_curriculum_to_library()
        return self._model

    def reorder_stage(self, stage_id: str, direction: str) -> RlTrainerModel:
        stages = sorted(
            [s.model_copy(deep=True) for s in self._model.curriculum.stages],
            key=lambda s: s.order,
        )
        idx = next((i for i, s in enumerate(stages) if s.id == stage_id), None)
        if idx is None:
            return self._model
        if direction == "up" and idx > 0:
            stages[idx], stages[idx - 1] = stages[idx - 1], stages[idx]
        elif direction == "down" and idx < len(stages) - 1:
            stages[idx], stages[idx + 1] = stages[idx + 1], stages[idx]
        self._model.curriculum.stages = self._renormalize_orders(stages)
        self._sync_curriculum_to_library()
        return self._model

    def add_gait(self, gait_id: str | None = None) -> RlTrainerModel:
        if gait_id:
            gait = build_gait(gait_id)
            gait.builtin = False
        else:
            gait = GaitType(id=new_id(), name="Custom gait", builtin=False)
        self._model.gaitTypes.append(gait)
        return self._model

    def delete_gait(self, gait_id: str) -> RlTrainerModel:
        self._model.gaitTypes = [g for g in self._model.gaitTypes if g.id != gait_id]
        return self._model

    def apply_gait_recommendation(self, gait_id: str) -> RlTrainerModel:
        gait, notes = recommend_gait(gait_id)
        for i, g in enumerate(self._model.gaitTypes):
            if g.id == gait_id:
                self._model.gaitTypes[i] = gait
                break
        else:
            self._model.gaitTypes.append(gait)
        self._model.recommendationNotes.extend(notes)
        return self._model

    def apply_stage_recommendation(self, stage_id: str) -> RlTrainerModel:
        rough = self._model.curriculum.terrainProfile == "rough"
        for i, s in enumerate(self._model.curriculum.stages):
            if s.id == stage_id:
                rec = recommend_stage_params(s, rough, self._model.machineProfile)
                s.command = rec.command
                s.disturbance = rec.disturbance
                s.timesteps = rec.timesteps
                s.termination = rec.termination
                s.advanceCriteria = rec.advanceCriteria
                s.targetLinVelX = rec.command.targetLinVelX
                self._model.curriculum.stages[i] = s
                self._model.recommendationNotes.extend(rec.notes)
                break
        self._sync_curriculum_to_library()
        return self._model

    def apply_curriculum_recommendation(self) -> RlTrainerModel:
        rough = self._model.curriculum.terrainProfile == "rough"
        notes = recommend_curriculum_timesteps(
            self._model.curriculum.stages,
            rough,
            self._model.machineProfile,
        )
        self._model.recommendationNotes.extend(notes)
        self._sync_curriculum_to_library()
        return self._model

    def list_checkpoints(self) -> list[CheckpointInfo]:
        return project_storage.list_checkpoints(
            self._model.projectName,
            self._model.trainingCheckpoint.checkpointDirectory,
        )

    @staticmethod
    def bootstrap_project(name: str) -> RlTrainerModel:
        robot = project_storage.load_robot_name(name) or name
        model = RlTrainerModel(projectName=name, robotName=robot)
        model.gaitTypes = default_gait_library()
        core = TrainerCore(model)
        core.apply_preset("velocity_tracking")
        core.refresh_machine_profile()
        return core.get_model()
