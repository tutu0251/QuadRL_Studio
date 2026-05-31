import { useState } from "react";
import type { CurriculumAdvanceCriteria, CurriculumStage, DisturbanceConfig, StageCommand } from "@rl-trainer-model";
import { STAGE_PARAM_HINTS, stageParamKey } from "@rl-trainer-model";
import { api } from "../../api/client";
import { ParamBoolField, ParamNumberField, ParamTextField } from "../../components/ParamField";
import { RewardTermList } from "../shared/RewardTermList";
import { TerminationFields } from "../shared/TerminationFields";
import { useTrainerStore } from "../../stores/trainerStore";
import { paramEnabled, patchStageParamEnabled } from "./stageParamUtils";

const INSPECTOR_TABS = [
  { id: "identity", label: "Identity" },
  { id: "command", label: "Command" },
  { id: "rewards", label: "Rewards" },
  { id: "disturbance", label: "Disturbance" },
  { id: "termination", label: "Termination" },
  { id: "advance", label: "Advance" },
] as const;

type InspectorTabId = (typeof INSPECTOR_TABS)[number]["id"];

export function StageInspector({ compact = false }: { compact?: boolean }) {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const selectedStageId = useTrainerStore((s) => s.selectedStageId);
  const log = useTrainerStore((s) => s.log);
  const [activeTab, setActiveTab] = useState<InspectorTabId>("identity");

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
  const activeRewards = stage.rewardTerms.filter((t) => t.enabled).length;

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
      {!compact && (
        <div className="stage-panel-header">
          <div>
            <h3>{stage.name}</h3>
            <span className="stage-inspector-meta mono">
              Stage {(stage.order ?? 0) + 1} · {stage.gaitTypeId}
            </span>
          </div>
          <button type="button" className="header-btn primary" onClick={() => void recommend()}>
            Auto-recommend
          </button>
        </div>
      )}

      {compact && (
        <div className="inspector-inline-bar">
          <span className="inspector-inline-title">{stage.name}</span>
          <span className="inspector-inline-meta mono">{stage.gaitTypeId}</span>
          <button type="button" className="header-btn" onClick={() => void recommend()}>
            Recommend
          </button>
        </div>
      )}

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
            {t.id === "rewards" && activeRewards > 0 ? (
              <span className="stage-tab-badge">{activeRewards}</span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="stage-inspector-scroll stage-inspector-tab-panel">
        {activeTab === "identity" && (
          <div className="inspector-tab-pane">
            <ParamTextField
              paramKey={stageParamKey("identity", "name")}
              label="name"
              hint={hint("identity.name")}
              enabled={paramEnabled(stage, "identity.name")}
              onEnabledChange={(v) => setParamFlag("identity.name", v)}
              value={stage.name}
              onChange={(v) => patchStage({ name: v })}
            />
            <ParamTextField
              paramKey={stageParamKey("identity", "description")}
              label="description"
              hint={hint("identity.description")}
              enabled={paramEnabled(stage, "identity.description")}
              onEnabledChange={(v) => setParamFlag("identity.description", v)}
              value={stage.description}
              onChange={(v) => patchStage({ description: v })}
            />
            <ParamFieldGaitSelect
              stage={stage}
              gaitOptions={gaitOptions}
              enabled={paramEnabled(stage, "identity.gait_type")}
              onEnabledChange={(v) => setParamFlag("identity.gait_type", v)}
              onChange={(gaitTypeId) => patchStage({ gaitTypeId })}
            />
            <ParamNumberField
              paramKey={stageParamKey("identity", "timesteps")}
              label="timesteps"
              hint={hint("identity.timesteps")}
              enabled={paramEnabled(stage, "identity.timesteps")}
              onEnabledChange={(v) => setParamFlag("identity.timesteps", v)}
              value={stage.timesteps}
              step={10_000}
              onChange={(v) => patchStage({ timesteps: Math.max(10_000, Math.round(v)) })}
            />
          </div>
        )}

        {activeTab === "command" && (
          <div className="inspector-tab-pane">
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
          </div>
        )}

        {activeTab === "rewards" && (
          <div className="inspector-tab-pane inspector-tab-pane-rewards">
            <RewardTermList
              terms={stage.rewardTerms}
              onChange={(terms) => patchStage({ rewardTerms: terms })}
            />
          </div>
        )}

        {activeTab === "disturbance" && (
          <div className="inspector-tab-pane">
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
          </div>
        )}

        {activeTab === "termination" && (
          <div className="inspector-tab-pane">
            <TerminationFields
              stage={stage}
              termination={stage.termination}
              onChange={(p) => patchStage({ termination: { ...stage.termination, ...p } })}
              onParamFlag={setParamFlag}
            />
          </div>
        )}

        {activeTab === "advance" && (
          <div className="inspector-tab-pane">
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
          </div>
        )}
      </div>
    </div>
  );
}

function ParamFieldGaitSelect({
  stage,
  gaitOptions,
  enabled,
  onEnabledChange,
  onChange,
}: {
  stage: CurriculumStage;
  gaitOptions: { id: string; name: string }[];
  enabled: boolean;
  onEnabledChange: (v: boolean) => void;
  onChange: (gaitTypeId: string) => void;
}) {
  const key = stageParamKey("identity", "gait_type");
  const checkboxId = `param-${key.replace(/[^a-z0-9.-]/gi, "-")}`;
  const hint = STAGE_PARAM_HINTS[key];
  return (
    <div className={`param-field param-field-checked ${enabled ? "" : "param-disabled"}`}>
      <label className="checkbox-row" title={hint}>
        <input
          id={checkboxId}
          type="checkbox"
          className="param-checkbox"
          checked={enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
        />
      </label>
      <label className="param-label-row" htmlFor={checkboxId}>
        <span className="param-label">gait_type</span>
        <span className="param-hint-icon" title={hint} aria-label={hint}>
          ⓘ
        </span>
      </label>
      <select
        className="param-input param-select"
        disabled={!enabled}
        value={stage.gaitTypeId}
        onChange={(e) => onChange(e.target.value)}
      >
        {gaitOptions.map((g) => (
          <option key={g.id} value={g.id}>
            {g.name}
          </option>
        ))}
      </select>
    </div>
  );
}
