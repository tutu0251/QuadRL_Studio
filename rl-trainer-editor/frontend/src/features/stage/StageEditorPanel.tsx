import type { CurriculumAdvanceCriteria, CurriculumStage, DisturbanceConfig, StageCommand } from "@rl-trainer-model";
import { api } from "../../api/client";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";
import { RewardTermList } from "../shared/RewardTermList";
import { TerminationFields } from "../shared/TerminationFields";
import { useTrainerStore } from "../../stores/trainerStore";

export function StageEditorPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const selectedStageId = useTrainerStore((s) => s.selectedStageId);
  const log = useTrainerStore((s) => s.log);

  if (!model || !project) return null;

  const stages = [...model.curriculum.stages].sort((a, b) => a.order - b.order);
  const stage = selectedStageId
    ? stages.find((s) => s.id === selectedStageId)
    : stages[model.curriculum.currentStageIndex] ?? stages[0];

  if (!stage) {
    return (
      <div className="tab-panel">
        <p className="empty-desc">Select a stage from the Curriculum tab, or add a stage to the pipeline.</p>
      </div>
    );
  }

  const gaitOptions = model.gaitTypes ?? [];

  const updateStages = async (next: CurriculumStage[]) => {
    try {
      setModel(
        await api.patchModel(project, {
          curriculum: { ...model.curriculum, stages: next },
        })
      );
    } catch (e) {
      log(String(e));
    }
  };

  const patchStage = (patch: Partial<CurriculumStage>) => {
    const next = stages.map((s) => (s.id === stage.id ? { ...s, ...patch } : s));
    void updateStages(next);
  };

  const patchCommand = (patch: Partial<StageCommand>) => {
    const cmd = { ...stage.command, ...patch };
    patchStage({
      command: cmd,
      targetLinVelX: cmd.targetLinVelX,
      targetAngVelZ: cmd.targetAngVelZ,
    });
  };

  const patchDisturbance = (patch: Partial<DisturbanceConfig>) => {
    patchStage({ disturbance: { ...stage.disturbance, ...patch } });
  };

  const patchAdvance = (patch: Partial<CurriculumAdvanceCriteria>) => {
    patchStage({ advanceCriteria: { ...stage.advanceCriteria, ...patch } });
  };

  const recommend = async () => {
    try {
      setModel(await api.recommendStage(project, stage.id));
      log(`Recommended params for stage '${stage.name}'`);
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <div className="tab-panel stage-panel">
      <div className="stage-panel-header">
        <h3>{stage.name}</h3>
        <button type="button" className="header-btn" onClick={() => void recommend()}>
          Auto-recommend
        </button>
      </div>

      <CollapsibleSection id="identity" title="Identity">
        <div className="param-field">
          <span className="param-label">name</span>
          <input
            className="param-input"
            value={stage.name}
            onChange={(e) => patchStage({ name: e.target.value })}
          />
        </div>
        <div className="param-field">
          <span className="param-label">description</span>
          <input
            className="param-input"
            value={stage.description}
            onChange={(e) => patchStage({ description: e.target.value })}
          />
        </div>
        <div className="param-field">
          <span className="param-label">gait_type</span>
          <select
            className="param-input param-select"
            value={stage.gaitTypeId}
            onChange={(e) => patchStage({ gaitTypeId: e.target.value })}
          >
            {gaitOptions.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
        <NumberField
          label="timesteps"
          value={stage.timesteps}
          step={10_000}
          onChange={(v) => patchStage({ timesteps: Math.max(10_000, Math.round(v)) })}
        />
      </CollapsibleSection>

      <CollapsibleSection id="command" title="Command">
        <NumberField label="target_lin_vel_x" value={stage.command.targetLinVelX} step={0.1} onChange={(v) => patchCommand({ targetLinVelX: v })} />
        <NumberField label="target_lin_vel_y" value={stage.command.targetLinVelY} step={0.1} onChange={(v) => patchCommand({ targetLinVelY: v })} />
        <NumberField label="target_ang_vel_z" value={stage.command.targetAngVelZ} step={0.1} onChange={(v) => patchCommand({ targetAngVelZ: v })} />
        <NumberField label="target_body_height" value={stage.command.targetBodyHeight} step={0.01} onChange={(v) => patchCommand({ targetBodyHeight: v })} />
        <NumberField label="gait_speed_scale" value={stage.command.gaitSpeedScale} step={0.05} onChange={(v) => patchCommand({ gaitSpeedScale: v })} />
      </CollapsibleSection>

      <CollapsibleSection id="rewards" title="Rewards & penalties" badge={`${stage.rewardTerms.filter((t) => t.enabled).length} active`}>
        <RewardTermList
          terms={stage.rewardTerms}
          onChange={(terms) => patchStage({ rewardTerms: terms })}
        />
      </CollapsibleSection>

      <CollapsibleSection id="disturbance" title="Disturbance">
        <Toggle label="Enable disturbances" checked={stage.disturbance.enabled} onChange={(v) => patchDisturbance({ enabled: v })} />
        <NumberField label="push_force_n" value={stage.disturbance.pushForceN} step={1} onChange={(v) => patchDisturbance({ pushForceN: v })} />
        <NumberField label="push_interval_steps" value={stage.disturbance.pushIntervalSteps} step={50} onChange={(v) => patchDisturbance({ pushIntervalSteps: Math.round(v) })} />
        <NumberField label="terrain_roughness" value={stage.disturbance.terrainRoughness} step={0.05} onChange={(v) => patchDisturbance({ terrainRoughness: v })} />
        <NumberField label="lateral_impulse_n" value={stage.disturbance.lateralImpulseN} step={1} onChange={(v) => patchDisturbance({ lateralImpulseN: v })} />
        <NumberField label="orientation_noise_rad" value={stage.disturbance.randomOrientationNoiseRad} step={0.01} onChange={(v) => patchDisturbance({ randomOrientationNoiseRad: v })} />
      </CollapsibleSection>

      <CollapsibleSection id="termination" title="Termination">
        <TerminationFields
          termination={stage.termination}
          onChange={(p) => patchStage({ termination: { ...stage.termination, ...p } })}
        />
      </CollapsibleSection>

      <CollapsibleSection id="advance" title="Advance criteria" defaultOpen={false}>
        <NumberField label="min_mean_episode_reward" value={stage.advanceCriteria.minMeanEpisodeReward} step={0.05} onChange={(v) => patchAdvance({ minMeanEpisodeReward: v })} />
        <NumberField label="min_episode_length_frac" value={stage.advanceCriteria.minEpisodeLengthFrac} step={0.05} onChange={(v) => patchAdvance({ minEpisodeLengthFrac: v })} />
        <NumberField label="max_fall_rate" value={stage.advanceCriteria.maxFallRate} step={0.05} onChange={(v) => patchAdvance({ maxFallRate: v })} />
      </CollapsibleSection>
    </div>
  );
}
