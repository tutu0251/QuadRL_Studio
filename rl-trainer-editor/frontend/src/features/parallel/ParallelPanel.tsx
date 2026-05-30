import type { VecEnvType } from "@rl-trainer-model";
import { api } from "../../api/client";
import { NumberField } from "../../components/NumberField";
import { useTrainerStore } from "../../stores/trainerStore";
import { batchDividesRollout, rolloutSize } from "../../utils/trainerMetrics";

export function ParallelPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);

  if (!model) return null;
  const par = model.parallel;
  const p = model.hyperparams;
  const rollout = rolloutSize(p, par.numEnvs);

  const patch = async (body: {
    numEnvs?: number;
    vecEnvType?: VecEnvType;
    nProc?: number | null;
  }) => {
    if (!project) return;
    try {
      setModel(await api.patchParallel(project, body));
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <div className="tab-panel parallel-panel">
      <div className="metric-inline">
        <span>Rollout buffer</span>
        <strong className="mono">{rollout}</strong>
        <span className={batchDividesRollout(p, par.numEnvs) ? "ok" : "warn"}>
          {batchDividesRollout(p, par.numEnvs) ? "batch OK" : "batch mismatch"}
        </span>
      </div>
      <div className="param-field">
        <span className="param-label">num_envs</span>
        <NumberField
          label="num_envs"
          value={par.numEnvs}
          step={1}
          onChange={(v) => void patch({ numEnvs: Math.max(1, Math.round(v)) })}
        />
      </div>
      <div className="param-field">
        <span className="param-label">vec_env_type</span>
        <select
          className="param-input param-select"
          value={par.vecEnvType}
          onChange={(e) => void patch({ vecEnvType: e.target.value as VecEnvType })}
        >
          <option value="subproc">subproc</option>
          <option value="dummy">dummy</option>
        </select>
      </div>
      <div className="param-field">
        <span className="param-label">n_proc</span>
        <NumberField
          label="n_proc"
          value={par.nProc ?? 0}
          step={1}
          onChange={(v) => void patch({ nProc: v > 0 ? Math.round(v) : null })}
        />
      </div>
      <p className="panel-hint">
        Recommend sets num_envs and vec env type from RAM, CPU cores, and GPU availability.
      </p>
    </div>
  );
}
