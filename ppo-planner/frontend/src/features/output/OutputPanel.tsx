import {
  BEST_MODEL_HINTS,
  BEST_MODEL_METRIC_LABELS,
  CHECKPOINT_FREQUENCY_LABELS,
  CHECKPOINT_HINTS,
  EXPORT_HINTS,
} from "@ppo-model";
import type {
  BestModelMetric,
  BestModelMode,
  CheckpointFrequency,
} from "@ppo-model";
import { FormatCheckboxGroup } from "../../components/FormatCheckboxGroup";
import { SectionCard } from "../../components/SectionCard";
import { TextField } from "../../components/TextField";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";
import { api } from "../../api/client";
import { usePlannerStore } from "../../stores/plannerStore";
import { exportConfigFilenames } from "../../utils/ppoMetrics";

export function OutputPanel() {
  const project = usePlannerStore((s) => s.project);
  const model = usePlannerStore((s) => s.model);
  const setModel = usePlannerStore((s) => s.setModel);
  const log = usePlannerStore((s) => s.log);

  if (!model) return null;

  const ckpt = model.checkpoint;
  const best = model.bestModel;
  const exp = model.exportFormat;

  const patch = async (body: Parameters<typeof api.patchOutput>[1]) => {
    if (!project) return;
    try {
      setModel(await api.patchOutput(project, body));
    } catch (e) {
      log(String(e));
    }
  };

  const exportNames = exportConfigFilenames(model.projectName, exp.formats);

  return (
    <div className="tab-panel output-panel">
      <div className="output-preview">
        <span className="output-preview-label">Export targets ({exportNames.length})</span>
        <ul className="output-preview-list">
          {exportNames.map((name) => (
            <li key={name}>
              <code className="output-preview-path">exports/{name}</code>
            </li>
          ))}
        </ul>
      </div>

      <SectionCard
        title="Checkpoints"
        description="Periodic and final SB3 .zip saves"
        disabled={!ckpt.enabled}
      >
        <Toggle
          label="Enable checkpoints"
          hint={CHECKPOINT_HINTS.enabled}
          checked={ckpt.enabled}
          onChange={(v) => void patch({ checkpoint: { enabled: v } })}
        />
        <TextField
          label="directory"
          hint={CHECKPOINT_HINTS.directory}
          value={ckpt.directory}
          disabled={!ckpt.enabled}
          onChange={(v) => void patch({ checkpoint: { directory: v } })}
        />
        <div className="param-field">
          <span className="param-label-row">
            <span className="param-label" title={CHECKPOINT_HINTS.frequency}>
              frequency
            </span>
            <span className="param-hint-icon" title={CHECKPOINT_HINTS.frequency} aria-label={CHECKPOINT_HINTS.frequency}>
              ⓘ
            </span>
          </span>
          <select
            className="param-input param-select"
            value={ckpt.frequency}
            disabled={!ckpt.enabled}
            title={CHECKPOINT_HINTS.frequency}
            onChange={(e) =>
              void patch({
                checkpoint: { frequency: e.target.value as CheckpointFrequency },
              })
            }
          >
            {(Object.keys(CHECKPOINT_FREQUENCY_LABELS) as CheckpointFrequency[]).map((k) => (
              <option key={k} value={k}>
                {CHECKPOINT_FREQUENCY_LABELS[k]}
              </option>
            ))}
          </select>
        </div>
        {ckpt.frequency === "steps" && (
          <NumberField
            label="frequency_steps"
            hint={CHECKPOINT_HINTS.frequencySteps}
            value={ckpt.frequencySteps}
            step={1000}
            min={1}
            disabled={!ckpt.enabled}
            onChange={(v) =>
              void patch({ checkpoint: { frequencySteps: Math.max(1, Math.round(v)) } })
            }
          />
        )}
        <TextField
          label="filename_template"
          hint={CHECKPOINT_HINTS.filenameTemplate}
          value={ckpt.filenameTemplate}
          disabled={!ckpt.enabled}
          placeholder="ppo_{stage_id}"
          onChange={(v) => void patch({ checkpoint: { filenameTemplate: v } })}
        />
        <NumberField
          label="keep_last_n"
          hint={CHECKPOINT_HINTS.keepLastN}
          value={ckpt.keepLastN}
          step={1}
          min={0}
          disabled={!ckpt.enabled}
          onChange={(v) => void patch({ checkpoint: { keepLastN: Math.max(0, Math.round(v)) } })}
        />
        <Toggle
          label="save_on_interrupt"
          hint={CHECKPOINT_HINTS.saveOnInterrupt}
          checked={ckpt.saveOnInterrupt}
          disabled={!ckpt.enabled}
          onChange={(v) => void patch({ checkpoint: { saveOnInterrupt: v } })}
        />
      </SectionCard>

      <SectionCard
        title="Best model"
        description="Copy the top checkpoint by eval metric"
        disabled={!best.enabled}
      >
        <Toggle
          label="Track best model"
          hint={BEST_MODEL_HINTS.enabled}
          checked={best.enabled}
          onChange={(v) => void patch({ bestModel: { enabled: v } })}
        />
        <div className="param-field">
          <span className="param-label-row">
            <span className="param-label" title={BEST_MODEL_HINTS.metric}>
              metric
            </span>
            <span className="param-hint-icon" title={BEST_MODEL_HINTS.metric} aria-label={BEST_MODEL_HINTS.metric}>
              ⓘ
            </span>
          </span>
          <select
            className="param-input param-select"
            value={best.metric}
            disabled={!best.enabled}
            title={BEST_MODEL_HINTS.metric}
            onChange={(e) =>
              void patch({ bestModel: { metric: e.target.value as BestModelMetric } })
            }
          >
            {(Object.keys(BEST_MODEL_METRIC_LABELS) as BestModelMetric[]).map((k) => (
              <option key={k} value={k}>
                {BEST_MODEL_METRIC_LABELS[k]}
              </option>
            ))}
          </select>
        </div>
        <div className="param-field">
          <span className="param-label-row">
            <span className="param-label" title={BEST_MODEL_HINTS.mode}>
              mode
            </span>
            <span className="param-hint-icon" title={BEST_MODEL_HINTS.mode} aria-label={BEST_MODEL_HINTS.mode}>
              ⓘ
            </span>
          </span>
          <select
            className="param-input param-select"
            value={best.mode}
            disabled={!best.enabled}
            title={BEST_MODEL_HINTS.mode}
            onChange={(e) => void patch({ bestModel: { mode: e.target.value as BestModelMode } })}
          >
            <option value="max">max</option>
            <option value="min">min</option>
          </select>
        </div>
        <TextField
          label="directory"
          hint={BEST_MODEL_HINTS.directory}
          value={best.directory}
          disabled={!best.enabled}
          onChange={(v) => void patch({ bestModel: { directory: v } })}
        />
        <TextField
          label="filename"
          hint={BEST_MODEL_HINTS.filename}
          value={best.filename}
          disabled={!best.enabled}
          onChange={(v) => void patch({ bestModel: { filename: v } })}
        />
        <NumberField
          label="min_improvement"
          hint={BEST_MODEL_HINTS.minImprovement}
          value={best.minImprovement}
          step={0.01}
          min={0}
          disabled={!best.enabled}
          onChange={(v) => void patch({ bestModel: { minImprovement: Math.max(0, v) } })}
        />
      </SectionCard>

      <SectionCard title="Export formats" description="Select one or more output files">
        <p className="panel-hint format-hint">{EXPORT_HINTS.formats}</p>
        <FormatCheckboxGroup
          selected={exp.formats}
          onChange={(formats) => void patch({ exportFormat: { formats } })}
        />
        <Toggle
          label="include_machine_profile"
          hint={EXPORT_HINTS.includeMachineProfile}
          checked={exp.includeMachineProfile}
          onChange={(v) => void patch({ exportFormat: { includeMachineProfile: v } })}
        />
        <Toggle
          label="include_recommendation_notes"
          hint={EXPORT_HINTS.includeRecommendationNotes}
          checked={exp.includeRecommendationNotes}
          onChange={(v) => void patch({ exportFormat: { includeRecommendationNotes: v } })}
        />
        <Toggle
          label="include_header_comments"
          hint={EXPORT_HINTS.includeHeaderComments}
          checked={exp.includeHeaderComments}
          onChange={(v) => void patch({ exportFormat: { includeHeaderComments: v } })}
        />
        <Toggle
          label="sort_keys"
          hint={EXPORT_HINTS.sortKeys}
          checked={exp.sortKeys}
          onChange={(v) => void patch({ exportFormat: { sortKeys: v } })}
        />
      </SectionCard>
    </div>
  );
}
