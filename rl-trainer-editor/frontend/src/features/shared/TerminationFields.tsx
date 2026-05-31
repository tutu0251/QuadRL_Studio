import type { TerminationConfig } from "@rl-trainer-model";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";

export function TerminationFields({
  termination,
  onChange,
}: {
  termination: TerminationConfig;
  onChange: (patch: Partial<TerminationConfig>) => void;
}) {
  return (
    <>
      <NumberField
        label="max_episode_steps"
        value={termination.maxEpisodeSteps}
        step={1}
        onChange={(v) => onChange({ maxEpisodeSteps: Math.round(v) })}
      />
      <NumberField
        label="fall_base_height_threshold"
        value={termination.fallBaseHeightThreshold}
        step={0.01}
        onChange={(v) => onChange({ fallBaseHeightThreshold: v })}
      />
      <NumberField
        label="max_tilt_rad"
        value={termination.maxTiltRad}
        step={0.05}
        onChange={(v) => onChange({ maxTiltRad: v })}
      />
      <NumberField
        label="max_joint_torque"
        value={termination.maxJointTorque ?? 0}
        step={1}
        onChange={(v) => onChange({ maxJointTorque: v > 0 ? v : null })}
      />
      <Toggle
        label="timeout_truncation"
        checked={termination.timeoutTruncation}
        onChange={(v) => onChange({ timeoutTruncation: v })}
      />
    </>
  );
}
