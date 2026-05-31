import type { CurriculumStage } from "@rl-trainer-model";
import { isStageParamEnabled } from "@rl-trainer-model";

export function patchStageParamEnabled(
  stage: CurriculumStage,
  key: string,
  enabled: boolean
): Record<string, boolean> {
  return { ...(stage.paramEnabled ?? {}), [key]: enabled };
}

export function paramEnabled(
  stage: CurriculumStage,
  key: string,
  fallback = true
): boolean {
  return isStageParamEnabled(stage, key, fallback);
}
