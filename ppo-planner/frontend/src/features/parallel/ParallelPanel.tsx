import type { VecEnvType } from "@ppo-model";
import { PARALLEL_HINTS } from "@ppo-model";
import { api } from "../../api/client";
import { NumberField } from "../../components/NumberField";
import { usePlannerStore } from "../../stores/plannerStore";
import { batchDividesRollout, maxRecommendedEnvs, rolloutSize } from "../../utils/ppoMetrics";

export function ParallelPanel() {
  const project = usePlannerStore((s) => s.project);
  const model = usePlannerStore((s) => s.model);
  const setModel = usePlannerStore((s) => s.setModel);
  const log = usePlannerStore((s) => s.log);

  if (!model) return null;
  const par = model.parallel;
  const p = model.params;
  const rollout = rolloutSize(p, par.numEnvs);
  const batchOk = batchDividesRollout(p, par.numEnvs);
  const recommendedMax = maxRecommendedEnvs(model.machineProfile);
  const nProcDisabled = par.vecEnvType === "dummy";

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
        <span className={batchOk ? "ok" : "warn"}>{batchOk ? "batch OK" : "batch mismatch"}</span>
      </div>

      <NumberField
        label="num_envs"
        hint={PARALLEL_HINTS.numEnvs}
        value={par.numEnvs}
        step={1}
        min={1}
        onChange={(v) => void patch({ numEnvs: Math.max(1, Math.round(v)) })}
      />

      {model.machineProfile && par.numEnvs > recommendedMax && (
        <p className="inline-warn" role="status">
          Above recommended max ({recommendedMax}) for this machine — may OOM or oversubscribe CPU.
        </p>
      )}

      <div className="param-field">
        <span className="param-label-row">
          <span className="param-label" title={PARALLEL_HINTS.vecEnvType}>
            vec_env_type
          </span>
          <span className="param-hint-icon" title={PARALLEL_HINTS.vecEnvType} aria-label={PARALLEL_HINTS.vecEnvType}>
            ⓘ
          </span>
        </span>
        <select
          className="param-input param-select"
          value={par.vecEnvType}
          title={PARALLEL_HINTS.vecEnvType}
          onChange={(e) => void patch({ vecEnvType: e.target.value as VecEnvType })}
        >
          <option value="subproc">subproc</option>
          <option value="dummy">dummy</option>
        </select>
      </div>

      <NumberField
        label="n_proc"
        hint={PARALLEL_HINTS.nProc}
        value={par.nProc ?? 0}
        step={1}
        disabled={nProcDisabled}
        onChange={(v) => void patch({ nProc: v > 0 ? Math.round(v) : null })}
      />

      {nProcDisabled && (
        <p className="inline-warn" role="status">
          n_proc is ignored for dummy vec env (cleared automatically).
        </p>
      )}

      {par.vecEnvType === "subproc" && par.numEnvs === 1 && (
        <p className="inline-warn" role="status">
          subproc with one env adds fork overhead — dummy is usually faster.
        </p>
      )}

      <p className="panel-hint">
        Recommend sets num_envs, vec env type, and n_proc from RAM, CPU cores, and GPU. Conflicts
        (e.g. n_proc &gt; num_envs, dummy + n_proc) are resolved on save.
      </p>
    </div>
  );
}
