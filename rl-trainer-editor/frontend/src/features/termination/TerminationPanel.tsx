import type { TerminationConfig } from "@rl-trainer-model";
import { STAGE_PARAM_HINTS, stageParamKey } from "@rl-trainer-model";
import { api } from "../../api/client";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";
import { TerminationTermList } from "../shared/TerminationTermList";
import { useTrainerStore } from "../../stores/trainerStore";

const hint = (name: string) => STAGE_PARAM_HINTS[stageParamKey("termination", name)];

export function TerminationPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);

  if (!model) return null;
  const t = model.termination;
  const terms = t.terminationTerms ?? [];

  const patch = async (body: Partial<TerminationConfig>) => {
    if (!project) return;
    try {
      setModel(
        await api.patchModel(project, {
          termination: { ...t, ...body },
        })
      );
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <div className="tab-panel termination-panel">
      <h4 className="inspector-subsection-title">Global thresholds</h4>
      <NumberField
        label="max_episode_steps"
        hint={hint("max_episode_steps")}
        value={t.maxEpisodeSteps}
        step={1}
        onChange={(v) => void patch({ maxEpisodeSteps: Math.round(v) })}
      />
      <NumberField
        label="fall_base_height_threshold"
        hint={hint("fall_base_height_threshold")}
        value={t.fallBaseHeightThreshold}
        step={0.01}
        onChange={(v) => void patch({ fallBaseHeightThreshold: v })}
      />
      <NumberField
        label="max_tilt_rad"
        hint={hint("max_tilt_rad")}
        value={t.maxTiltRad}
        step={0.05}
        onChange={(v) => void patch({ maxTiltRad: v })}
      />
      <NumberField
        label="max_joint_torque"
        hint={hint("max_joint_torque")}
        value={t.maxJointTorque ?? 0}
        step={1}
        onChange={(v) => void patch({ maxJointTorque: v > 0 ? v : null })}
      />
      <Toggle
        label="timeout_truncation"
        hint={hint("timeout_truncation")}
        checked={t.timeoutTruncation}
        onChange={(v) => void patch({ timeoutTruncation: v })}
      />

      <h4 className="inspector-subsection-title">Termination conditions</h4>
      <TerminationTermList
        terms={terms}
        onChange={(next) => void patch({ terminationTerms: next })}
      />
    </div>
  );
}
