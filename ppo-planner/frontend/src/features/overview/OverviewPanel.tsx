import { usePlannerStore } from "../../stores/plannerStore";
import { MetricCard } from "../../components/MetricCard";
import {
  batchDividesRollout,
  formatTimesteps,
  resolvedDevice,
  rolloutSize,
} from "../../utils/ppoMetrics";

export function OverviewPanel() {
  const model = usePlannerStore((s) => s.model);
  const validation = usePlannerStore((s) => s.validation);

  if (!model) {
    return (
      <div className="overview-panel empty">
        <div className="hero-card">
          <h1>PPO Planner</h1>
          <p className="hero-lead">
            Tune stable-baselines3 PPO hyperparameters for your quadruped RL run. Defaults are
            chosen from this machine&apos;s CPU, RAM, and GPU.
          </p>
        </div>
        <div className="workflow-card">
          <h2>Workflow</h2>
          <ol className="workflow-steps">
            <li>
              <span className="step-num">1</span>
              <span>Complete the four editors → sensor RL export</span>
            </li>
            <li>
              <span className="step-num">2</span>
              <span>File → select project (auto-bootstraps PPO config)</span>
            </li>
            <li>
              <span className="step-num">3</span>
              <span>Recommend → adjust params → Validate → Export YAML</span>
            </li>
          </ol>
        </div>
        <p className="overview-footnote">
          Export writes <code>exports/ppo_&lt;project&gt;_config.yaml</code> next to your robot
          package.
        </p>
      </div>
    );
  }

  const p = model.params;
  const rollout = rolloutSize(p);
  const batchOk = batchDividesRollout(p);
  const device = resolvedDevice(p, model.machineProfile);

  return (
    <div className="overview-panel">
      <header className="overview-header">
        <div>
          <h2>{model.robotName}</h2>
          <p className="overview-subtitle">
            Project <span className="mono">{model.projectName}</span> · PPO · SB3-compatible
          </p>
        </div>
        <div className="overview-badges">
          <span className={`badge badge-device badge-${device}`}>{device.toUpperCase()}</span>
          <span className={`badge ${model.useRecommended ? "badge-auto" : "badge-manual"}`}>
            {model.useRecommended ? "Auto-tuned" : "Manual"}
          </span>
          {validation && (
            <span className={`badge ${validation.valid ? "badge-ok" : "badge-err"}`}>
              {validation.valid ? "Valid" : `${validation.errors.length} errors`}
            </span>
          )}
        </div>
      </header>

      <div className="metric-grid">
        <MetricCard
          label="Rollout buffer"
          value={String(rollout)}
          sub={`${p.nSteps} × ${p.numEnvs} envs`}
          variant="accent"
        />
        <MetricCard
          label="Batch size"
          value={String(p.batchSize)}
          sub={batchOk ? "divides rollout" : "may truncate minibatch"}
          variant={batchOk ? "ok" : "warn"}
        />
        <MetricCard
          label="Training steps"
          value={formatTimesteps(p.totalTimesteps)}
          sub={`${p.totalTimesteps.toLocaleString()} total`}
        />
        <MetricCard
          label="Updates / run"
          value={rollout > 0 ? String(Math.floor(p.totalTimesteps / rollout)) : "—"}
          sub={`${p.nEpochs} epochs each`}
        />
      </div>

      {!batchOk && (
        <div className="banner banner-warn" role="status">
          Rollout size ({rollout}) is not divisible by batch_size ({p.batchSize}). Consider
          adjusting batch_size or n_steps × num_envs.
        </div>
      )}

      {validation && !validation.valid && (
        <div className="banner banner-err" role="alert">
          {validation.errors[0]?.message ?? "Validation failed"}
          {validation.errors.length > 1 && ` (+${validation.errors.length - 1} more)`}
        </div>
      )}

      {model.recommendationNotes.length > 0 && (
        <section className="insight-card">
          <h3>Machine recommendations</h3>
          <ul className="insight-list">
            {model.recommendationNotes.map((n, i) => (
              <li key={i}>
                <span className="insight-dot" aria-hidden />
                {n}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="params-preview-card">
        <h3>Hyperparameter snapshot</h3>
        <table className="params-table">
          <tbody>
            <tr>
              <td>learning_rate</td>
              <td className="mono">{p.learningRate}</td>
            </tr>
            <tr>
              <td>n_steps / batch / epochs</td>
              <td className="mono">
                {p.nSteps} / {p.batchSize} / {p.nEpochs}
              </td>
            </tr>
            <tr>
              <td>γ / λ / clip</td>
              <td className="mono">
                {p.gamma} / {p.gaeLambda} / {p.clipRange}
              </td>
            </tr>
            <tr>
              <td>ent_coef / vf_coef</td>
              <td className="mono">
                {p.entCoef} / {p.vfCoef}
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="export-hints">
        <p className="export-hints-title">On export</p>
        <ul>
          <li>
            <code>ppo_{model.projectName}_config.yaml</code>
          </li>
        </ul>
      </section>
    </div>
  );
}
