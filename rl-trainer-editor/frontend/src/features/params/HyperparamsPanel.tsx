import type { PpoHyperparams } from "@rl-trainer-model";
import { RL_HYPERPARAM_GROUPS, RL_HYPERPARAM_HINTS } from "@rl-trainer-model";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { NumberField } from "../../components/NumberField";
import { api } from "../../api/client";
import { useTrainerStore } from "../../stores/trainerStore";
import { batchDividesRollout, rolloutSize } from "../../utils/trainerMetrics";

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

export function HyperparamsPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);

  if (!model) return null;
  const p = model.hyperparams;
  const par = model.parallel;

  const patch = async (body: Partial<PpoHyperparams> & { useRecommended?: boolean }) => {
    if (!project) return;
    try {
      setModel(await api.patchHyperparams(project, body));
    } catch (e) {
      log(String(e));
    }
  };

  const rollout = rolloutSize(p, par.numEnvs);
  const batchOk = batchDividesRollout(p, par.numEnvs);

  const renderField = (key: keyof PpoHyperparams) => {
    if (key === "device") {
      return (
        <div className="param-field" key={key}>
          <span className="param-label" title={RL_HYPERPARAM_HINTS.device}>
            {LABELS.device}
          </span>
          <select
            className="param-input param-select"
            value={p.device}
            onChange={(e) => void patch({ device: e.target.value as PpoHyperparams["device"] })}
          >
            <option value="auto">auto</option>
            <option value="cpu">cpu</option>
            <option value="cuda">cuda</option>
          </select>
        </div>
      );
    }
    return (
      <div className="param-field" key={key}>
        <span className="param-label" title={RL_HYPERPARAM_HINTS[key]}>
          {LABELS[key]}
        </span>
        <NumberField
          label={LABELS[key]}
          hint={RL_HYPERPARAM_HINTS[key]}
          value={p[key] as number}
          step={stepFor(key)}
          onChange={(v) => void patch({ [key]: v } as Partial<PpoHyperparams>)}
        />
      </div>
    );
  };

  return (
    <div className="tab-panel hyperparams-panel">
      {!batchOk && (
        <div className="inline-warn">
          Rollout {rollout} not divisible by batch {p.batchSize}
        </div>
      )}
      {RL_HYPERPARAM_GROUPS.map((g, i) => (
        <CollapsibleSection key={g.id} id={g.id} title={g.label} defaultOpen={i < 2}>
          {g.keys.map(renderField)}
        </CollapsibleSection>
      ))}
    </div>
  );
}
