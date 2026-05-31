import type { PpoHyperparams } from "@ppo-model";
import { PPO_PARAM_GROUPS, PPO_PARAM_HINTS } from "@ppo-model";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";
import { api } from "../../api/client";
import { usePlannerStore } from "../../stores/plannerStore";
import { batchDividesRollout, rolloutSize } from "../../utils/ppoMetrics";

const LABELS: Record<keyof PpoHyperparams, string> = {
  learningRate: "learning_rate",
  nSteps: "n_steps",
  batchSize: "batch_size",
  nEpochs: "n_epochs",
  gamma: "gamma",
  gaeLambda: "gae_lambda",
  clipRange: "clip_range",
  entCoef: "ent_coef",
  vfCoef: "vf_coef",
  maxGradNorm: "max_grad_norm",
  totalTimesteps: "total_timesteps",
  device: "device",
};

function stepFor(key: keyof PpoHyperparams): number {
  if (key === "learningRate" || key === "entCoef") return 0.0001;
  if (key === "gamma" || key === "gaeLambda" || key === "clipRange") return 0.01;
  if (key === "totalTimesteps" || key === "nSteps" || key === "batchSize") return 1;
  return 0.1;
}

export function ParamsPanel({ embedded = false }: { embedded?: boolean }) {
  const project = usePlannerStore((s) => s.project);
  const model = usePlannerStore((s) => s.model);
  const setModel = usePlannerStore((s) => s.setModel);
  const log = usePlannerStore((s) => s.log);

  if (!model) {
    if (embedded) return null;
    return (
      <div className="unity-panel params-panel">
        <div className="panel-header">Hyperparameters</div>
        <div className="panel-empty-state">
          <p className="empty-desc">Select a project to edit PPO settings</p>
        </div>
      </div>
    );
  }

  const patch = async (body: Partial<PpoHyperparams> & { useRecommended?: boolean }) => {
    if (!project) return;
    try {
      const m = await api.patchParams(project, body);
      setModel(m);
    } catch (e) {
      log(String(e));
    }
  };

  const numEnvs = model.parallel.numEnvs;
  const rollout = rolloutSize(model.params, numEnvs);
  const batchOk = batchDividesRollout(model.params, numEnvs);

  const renderField = (key: keyof PpoHyperparams) => {
    if (key === "device") {
      return (
        <div className="param-field" key={key}>
          <span className="param-label" title={PPO_PARAM_HINTS.device}>
            {LABELS.device}
          </span>
          <select
            className="param-input param-select"
            value={model.params.device}
            onChange={(e) =>
              void patch({ device: e.target.value as PpoHyperparams["device"] })
            }
          >
            <option value="auto">auto</option>
            <option value="cpu">cpu</option>
            <option value="cuda">cuda</option>
          </select>
        </div>
      );
    }
    const v = model.params[key] as number;
    return (
      <NumberField
        key={key}
        label={LABELS[key]}
        hint={PPO_PARAM_HINTS[key]}
        value={v}
        step={stepFor(key)}
        status={key === "batchSize" && !batchOk ? "warn" : undefined}
        onChange={(n) => void patch({ [key]: n } as Partial<PpoHyperparams>)}
      />
    );
  };

  const body = (
    <>
      <div className={embedded ? "params-toolbar tab-toolbar" : "params-toolbar"}>
        <Toggle
          label="Auto-apply recommendations"
          hint="When enabled, Recommend overwrites params for this machine"
          checked={model.useRecommended}
          onChange={(v) => void patch({ useRecommended: v })}
        />
      </div>

      <div className={embedded ? "params-scroll tab-scroll" : "params-scroll"}>
        {PPO_PARAM_GROUPS.map((g, i) => (
          <CollapsibleSection
            key={g.id}
            id={g.id}
            title={g.label}
            defaultOpen={i < 2}
            badge={String(g.keys.length)}
          >
            {g.keys.map(renderField)}
          </CollapsibleSection>
        ))}
      </div>
    </>
  );

  if (embedded) {
    return <div className="tab-panel params-panel-embedded">{body}</div>;
  }

  return (
    <div className="unity-panel params-panel">
      <div className="panel-header">
        <span>Hyperparameters</span>
        <span className={`panel-header-meta ${batchOk ? "meta-ok" : "meta-warn"}`}>
          rollout {rollout}
        </span>
      </div>
      {body}
    </div>
  );
}
