import type { CurriculumStage } from "@rl-trainer-model";

/** Resolved gate-type IDs for a stage (supports legacy gaitTypeId). */
export function stageGaitTypeIds(stage: Pick<CurriculumStage, "gaitTypeIds" | "gaitTypeId">): string[] {
  if (stage.gaitTypeIds?.length) return [...stage.gaitTypeIds];
  if (stage.gaitTypeId) return [stage.gaitTypeId];
  return ["none"];
}

export function formatStageGaitTypes(stage: Pick<CurriculumStage, "gaitTypeIds" | "gaitTypeId">): string {
  return stageGaitTypeIds(stage).join(", ");
}
