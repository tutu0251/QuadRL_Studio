import type { CurriculumStage, TerminationConfig, TerminationTerm } from "@rl-trainer-model";
import { STAGE_PARAM_HINTS, stageParamKey } from "@rl-trainer-model";
import { ParamBoolField, ParamNumberField } from "../../components/ParamField";
import { paramEnabled } from "../stage/stageParamUtils";
import { TerminationTermList } from "./TerminationTermList";

export function TerminationFields({
  stage,
  termination,
  onChange,
  onParamFlag,
}: {
  stage: CurriculumStage;
  termination: TerminationConfig;
  onChange: (patch: Partial<TerminationConfig>) => void;
  onParamFlag: (key: string, enabled: boolean) => void;
  onTermsChange?: (terms: TerminationTerm[]) => void;
}) {
  const hint = (name: string) => STAGE_PARAM_HINTS[stageParamKey("termination", name)];
  const terms = termination.terminationTerms ?? [];

  return (
    <>
      <h4 className="inspector-subsection-title">Global thresholds</h4>
      <ParamNumberField
        paramKey={stageParamKey("termination", "max_episode_steps")}
        label="max_episode_steps"
        hint={hint("max_episode_steps")}
        enabled={paramEnabled(stage, "termination.max_episode_steps")}
        onEnabledChange={(v) => onParamFlag("termination.max_episode_steps", v)}
        value={termination.maxEpisodeSteps}
        step={1}
        onChange={(v) => onChange({ maxEpisodeSteps: Math.round(v) })}
      />
      <ParamNumberField
        paramKey={stageParamKey("termination", "fall_base_height_threshold")}
        label="fall_base_height_threshold"
        hint={hint("fall_base_height_threshold")}
        enabled={paramEnabled(stage, "termination.fall_base_height_threshold")}
        onEnabledChange={(v) => onParamFlag("termination.fall_base_height_threshold", v)}
        value={termination.fallBaseHeightThreshold}
        step={0.01}
        onChange={(v) => onChange({ fallBaseHeightThreshold: v })}
      />
      <ParamNumberField
        paramKey={stageParamKey("termination", "max_tilt_rad")}
        label="max_tilt_rad"
        hint={hint("max_tilt_rad")}
        enabled={paramEnabled(stage, "termination.max_tilt_rad")}
        onEnabledChange={(v) => onParamFlag("termination.max_tilt_rad", v)}
        value={termination.maxTiltRad}
        step={0.05}
        onChange={(v) => onChange({ maxTiltRad: v })}
      />
      <ParamNumberField
        paramKey={stageParamKey("termination", "max_joint_torque")}
        label="max_joint_torque"
        hint={hint("max_joint_torque")}
        enabled={paramEnabled(stage, "termination.max_joint_torque", termination.maxJointTorque != null)}
        onEnabledChange={(v) => onParamFlag("termination.max_joint_torque", v)}
        value={termination.maxJointTorque ?? 0}
        step={1}
        onChange={(v) => onChange({ maxJointTorque: v > 0 ? v : null })}
      />
      <ParamBoolField
        paramKey={stageParamKey("termination", "timeout_truncation")}
        label="timeout_truncation"
        hint={hint("timeout_truncation")}
        checked={termination.timeoutTruncation}
        onChange={(v) => {
          onChange({ timeoutTruncation: v });
          onParamFlag("termination.timeout_truncation", v);
        }}
      />

      <h4 className="inspector-subsection-title">Termination conditions</h4>
      <TerminationTermList
        terms={terms}
        stage={stage}
        onParamFlag={onParamFlag}
        onChange={(next) => onChange({ terminationTerms: next })}
      />
    </>
  );
}
