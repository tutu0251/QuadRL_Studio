import { useState } from "react";
import type { CurriculumAdvanceCriteria, CurriculumStage, DisturbanceConfig, StageCommand } from "@rl-trainer-model";
import { STAGE_PARAM_HINTS, stageParamKey } from "@rl-trainer-model";
import { api } from "../../api/client";
import { InspectorParamGrid } from "../../components/InspectorParamGrid";
import { ParamBoolField, ParamNumberField } from "../../components/ParamField";
import { stageGaitTypeIds } from "./stageGaitUtils";
import { RewardTermList } from "../shared/RewardTermList";
import { TerminationFields } from "../shared/TerminationFields";
import { useTrainerStore } from "../../stores/trainerStore";
import { paramEnabled, patchStageParamEnabled } from "./stageParamUtils";

const INSPECTOR_TABS = [
  { id: "command", label: "Command" },
  { id: "rewards", label: "Reward/Penalty" },
  { id: "disturbance", label: "Disturbance" },
  { id: "termination", label: "Termination" },
  { id: "advance", label: "Advance" },
] as const;

type InspectorTabId = (typeof INSPECTOR_TABS)[number]["id"];

function InlineGaitChips({
  options,
  value,
  disabled,
  onChange,
  hint,
}: {
  options: { id: string; name: string }[];
  value: string[];
  disabled?: boolean;
  onChange: (ids: string[]) => void;
  hint?: string;
}) {
  const toggle = (id: string) => {
    if (value.includes(id)) {
      if (value.length <= 1) return;
      onChange(value.filter((x) => x !== id));
    } else {
      onChange([...value, id]);
    }
  };

  return (
    <div
      className="chip-row inspector-inline-gait"
      role="group"
      aria-label="gate type"
      title={hint}
    >
      {options.map((o) => {
        const selected = value.includes(o.id);
        return (
          <button
            key={o.id}
            type="button"
            className={`chip-btn ${selected ? "active" : ""}`}
            disabled={disabled}
            aria-pressed={selected}
            onClick={() => toggle(o.id)}
          >
            {o.name}
          </button>
        );
      })}
    </div>
  );
}

export function StageInspector({ compact = false }: { compact?: boolean }) {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const selectedStageId = useTrainerStore((s) => s.selectedStageId);
  const log = useTrainerStore((s) => s.log);
  const [activeTab, setActiveTab] = useState<InspectorTabId>("command");

  if (!model || !project) return null;

  const stages = [...model.curriculum.stages].sort((a, b) => a.order - b.order);
  const stage = selectedStageId ? stages.find((s) => s.id === selectedStageId) : null;

  if (!stage) {
    return (
      <div className={`stage-inspector-empty ${compact ? "compact" : ""}`}>
        <p className="empty-desc">Select a stage from the pipeline to edit its parameters.</p>
      </div>
    );
  }

  const gaitOptions = model.gaitTypes ?? [];
  const selectedGaitIds = stageGaitTypeIds(stage);
  const activeRewardPenalty = stage.rewardTerms.filter((t) => t.enabled).length;
  const gaitEnabled = paramEnabled(stage, "identity.gait_type");
  const timestepsEnabled = paramEnabled(stage, "identity.timesteps");
  const titleTooltip =
    stage.description.trim() || STAGE_PARAM_HINTS["identity.description"] || "Stage description";

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

  const setParamFlag = (key: string, enabled: boolean) => {
    patchStage({ paramEnabled: patchStageParamEnabled(stage, key, enabled) });
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

  const hint = (key: string) => STAGE_PARAM_HINTS[key];

  return (
    <div className={`stage-inspector ${compact ? "compact" : ""}`}>
      <div className="inspector-inline-bar">
        <input
          type="text"
          className="inspector-inline-title-input"
          value={stage.name}
          title={titleTooltip}
          aria-label="Stage name"
          onChange={(e) => patchStage({ name: e.target.value })}
        />
        <div className="inspector-inline-group" title={hint("identity.gait_type")}>
          <span className="inspector-inline-label">gate</span>
          <InlineGaitChips
            options={gaitOptions}
            value={selectedGaitIds}
            disabled={!gaitEnabled}
            hint={hint("identity.gait_type")}
            onChange={(gaitTypeIds) => patchStage({ gaitTypeIds })}
          />
        </div>
        <div className="inspector-inline-group" title={hint("identity.timesteps")}>
          <span className="inspector-inline-label">steps</span>
          <input
            type="number"
            className="inspector-inline-steps-input mono"
            value={stage.timesteps}
            disabled={!timestepsEnabled}
            step={10_000}
            min={10_000}
            aria-label="Timesteps"
            onChange={(e) =>
              patchStage({ timesteps: Math.max(10_000, Math.round(parseFloat(e.target.value) || 0)) })
            }
          />
        </div>
        <button type="button" className="header-btn inspector-inline-recommend" onClick={() => void recommend()}>
          {compact ? "Recommend" : "Auto-recommend"}
        </button>
      </div>

      <div className="stage-inspector-tabs tab-bar tab-bar-segmented stage-category-tabs" role="tablist">
        {INSPECTOR_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={activeTab === t.id}
            className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
            {t.id === "rewards" && activeRewardPenalty > 0 ? (
              <span className="stage-tab-badge">{activeRewardPenalty}</span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="stage-inspector-scroll stage-inspector-tab-panel">
        {activeTab === "command" && (
          <InspectorParamGrid>
            <ParamNumberField
              paramKey={stageParamKey("command", "target_lin_vel_x")}
              label="target_lin_vel_x"
              hint={hint("command.target_lin_vel_x")}
              enabled={paramEnabled(stage, "command.target_lin_vel_x")}
              onEnabledChange={(v) => setParamFlag("command.target_lin_vel_x", v)}
              value={stage.command.targetLinVelX}
              step={0.1}
              onChange={(v) => patchCommand({ targetLinVelX: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("command", "target_lin_vel_y")}
              label="target_lin_vel_y"
              hint={hint("command.target_lin_vel_y")}
              enabled={paramEnabled(stage, "command.target_lin_vel_y")}
              onEnabledChange={(v) => setParamFlag("command.target_lin_vel_y", v)}
              value={stage.command.targetLinVelY}
              step={0.1}
              onChange={(v) => patchCommand({ targetLinVelY: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("command", "target_ang_vel_z")}
              label="target_ang_vel_z"
              hint={hint("command.target_ang_vel_z")}
              enabled={paramEnabled(stage, "command.target_ang_vel_z")}
              onEnabledChange={(v) => setParamFlag("command.target_ang_vel_z", v)}
              value={stage.command.targetAngVelZ}
              step={0.1}
              onChange={(v) => patchCommand({ targetAngVelZ: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("command", "target_body_height")}
              label="target_body_height"
              hint={hint("command.target_body_height")}
              enabled={paramEnabled(stage, "command.target_body_height")}
              onEnabledChange={(v) => setParamFlag("command.target_body_height", v)}
              value={stage.command.targetBodyHeight}
              step={0.01}
              onChange={(v) => patchCommand({ targetBodyHeight: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("command", "gait_speed_scale")}
              label="gait_speed_scale"
              hint={hint("command.gait_speed_scale")}
              enabled={paramEnabled(stage, "command.gait_speed_scale")}
              onEnabledChange={(v) => setParamFlag("command.gait_speed_scale", v)}
              value={stage.command.gaitSpeedScale}
              step={0.05}
              onChange={(v) => patchCommand({ gaitSpeedScale: v })}
            />
          </InspectorParamGrid>
        )}

        {activeTab === "rewards" && (
          <InspectorParamGrid className="inspector-param-grid-rewards">
            <RewardTermList
              terms={stage.rewardTerms}
              onChange={(terms) => patchStage({ rewardTerms: terms })}
            />
          </InspectorParamGrid>
        )}

        {activeTab === "disturbance" && (
          <InspectorParamGrid>
            <ParamBoolField
              paramKey={stageParamKey("disturbance", "enabled")}
              label="enable_disturbances"
              hint={hint("disturbance.enabled")}
              checked={stage.disturbance.enabled}
              onChange={(v) => {
                patchDisturbance({ enabled: v });
                setParamFlag("disturbance.enabled", v);
              }}
            />
            <ParamNumberField
              paramKey={stageParamKey("disturbance", "push_force_n")}
              label="push_force_n"
              hint={hint("disturbance.push_force_n")}
              enabled={paramEnabled(stage, "disturbance.push_force_n")}
              onEnabledChange={(v) => setParamFlag("disturbance.push_force_n", v)}
              value={stage.disturbance.pushForceN}
              step={1}
              onChange={(v) => patchDisturbance({ pushForceN: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("disturbance", "push_interval_steps")}
              label="push_interval_steps"
              hint={hint("disturbance.push_interval_steps")}
              enabled={paramEnabled(stage, "disturbance.push_interval_steps")}
              onEnabledChange={(v) => setParamFlag("disturbance.push_interval_steps", v)}
              value={stage.disturbance.pushIntervalSteps}
              step={50}
              onChange={(v) => patchDisturbance({ pushIntervalSteps: Math.round(v) })}
            />
            <ParamNumberField
              paramKey={stageParamKey("disturbance", "terrain_roughness")}
              label="terrain_roughness"
              hint={hint("disturbance.terrain_roughness")}
              enabled={paramEnabled(stage, "disturbance.terrain_roughness")}
              onEnabledChange={(v) => setParamFlag("disturbance.terrain_roughness", v)}
              value={stage.disturbance.terrainRoughness}
              step={0.05}
              onChange={(v) => patchDisturbance({ terrainRoughness: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("disturbance", "lateral_impulse_n")}
              label="lateral_impulse_n"
              hint={hint("disturbance.lateral_impulse_n")}
              enabled={paramEnabled(stage, "disturbance.lateral_impulse_n")}
              onEnabledChange={(v) => setParamFlag("disturbance.lateral_impulse_n", v)}
              value={stage.disturbance.lateralImpulseN}
              step={1}
              onChange={(v) => patchDisturbance({ lateralImpulseN: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("disturbance", "orientation_noise_rad")}
              label="orientation_noise_rad"
              hint={hint("disturbance.orientation_noise_rad")}
              enabled={paramEnabled(stage, "disturbance.orientation_noise_rad")}
              onEnabledChange={(v) => setParamFlag("disturbance.orientation_noise_rad", v)}
              value={stage.disturbance.randomOrientationNoiseRad}
              step={0.01}
              onChange={(v) => patchDisturbance({ randomOrientationNoiseRad: v })}
            />
          </InspectorParamGrid>
        )}

        {activeTab === "termination" && (
          <InspectorParamGrid>
            <TerminationFields
              stage={stage}
              termination={stage.termination}
              onChange={(p) => patchStage({ termination: { ...stage.termination, ...p } })}
              onParamFlag={setParamFlag}
            />
          </InspectorParamGrid>
        )}

        {activeTab === "advance" && (
          <InspectorParamGrid>
            <ParamNumberField
              paramKey={stageParamKey("advance", "min_mean_episode_reward")}
              label="min_mean_episode_reward"
              hint={hint("advance.min_mean_episode_reward")}
              enabled={paramEnabled(stage, "advance.min_mean_episode_reward")}
              onEnabledChange={(v) => setParamFlag("advance.min_mean_episode_reward", v)}
              value={stage.advanceCriteria.minMeanEpisodeReward}
              step={0.05}
              onChange={(v) => patchAdvance({ minMeanEpisodeReward: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("advance", "min_episode_length_frac")}
              label="min_episode_length_frac"
              hint={hint("advance.min_episode_length_frac")}
              enabled={paramEnabled(stage, "advance.min_episode_length_frac")}
              onEnabledChange={(v) => setParamFlag("advance.min_episode_length_frac", v)}
              value={stage.advanceCriteria.minEpisodeLengthFrac}
              step={0.05}
              onChange={(v) => patchAdvance({ minEpisodeLengthFrac: v })}
            />
            <ParamNumberField
              paramKey={stageParamKey("advance", "max_fall_rate")}
              label="max_fall_rate"
              hint={hint("advance.max_fall_rate")}
              enabled={paramEnabled(stage, "advance.max_fall_rate")}
              onEnabledChange={(v) => setParamFlag("advance.max_fall_rate", v)}
              value={stage.advanceCriteria.maxFallRate}
              step={0.05}
              onChange={(v) => patchAdvance({ maxFallRate: v })}
            />
          </InspectorParamGrid>
        )}
      </div>
    </div>
  );
}
