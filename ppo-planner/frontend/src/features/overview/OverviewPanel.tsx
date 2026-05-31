import { usePlannerStore } from "../../stores/plannerStore";
import { MetricCard } from "../../components/MetricCard";
import {
  batchDividesRollout,
  bestModelSummary,
  checkpointSummary,
  exportConfigFilenames,
  exportFormatsSummary,
  formatTimesteps,
  parallelSummary,
  resolvedDevice,
  rolloutSize,
} from "../../utils/ppoMetrics";

const WORKFLOW = [
  { step: 1, title: "Pipeline", body: "Complete geometry → physics → control → sensor editors" },
  { step: 2, title: "Load project", body: "File menu — auto-bootstraps PPO config with machine defaults" },
  { step: 3, title: "Tune & validate", body: "Recommend → adjust hyperparams, parallel, and output tabs" },
  { step: 4, title: "Export", body: "Writes training config to exports/ for the training launcher" },
] as const;

export function OverviewPanel() {
  const model = usePlannerStore((s) => s.model);
  const validation = usePlannerStore((s) => s.validation);

  if (!model) {
    return (
      <div className="overview-panel overview-empty">
        <div className="welcome-grid">
          <div className="welcome-hero">
            <p className="welcome-kicker">QuadRL Studio</p>
            <h1>PPO Planner</h1>
            <p className="welcome-lead">
              Configure stable-baselines3 PPO hyperparameters, parallel envs, checkpoints, and
              export format — tuned to your machine&apos;s CPU, RAM, and GPU.
            </p>
          </div>
          <div className="welcome-card">
            <h2>Workflow</h2>
            <ol className="pipeline-steps">
              {WORKFLOW.map((w) => (
                <li key={w.step}>
                  <span className="pipeline-num">{w.step}</span>
                  <div>
                    <strong>{w.title}</strong>
                    <p>{w.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
        <p className="welcome-footnote">
          Export path: <code>exports/ppo_&lt;project&gt;_config.yaml</code>
        </p>
      </div>
    );
  }

  const p = model.params;
  const par = model.parallel;
  const rollout = rolloutSize(p, par.numEnvs);
  const batchOk = batchDividesRollout(p, par.numEnvs);
  const device = resolvedDevice(p, model.machineProfile);
  const exportNames = exportConfigFilenames(model.projectName, model.exportFormat.formats);
  const updates = rollout > 0 ? Math.floor(p.totalTimesteps / rollout) : 0;

  return (
    <div className="overview-panel overview-loaded">
      <header className="dash-header">
        <div className="dash-title-block">
          <p className="dash-kicker">Training plan</p>
          <h2>{model.robotName}</h2>
          <p className="dash-subtitle">
            <span className="mono">{model.projectName}</span> · PPO · SB3
          </p>
        </div>
        <div className="dash-badges">
          <span className={`pill pill-device pill-${device}`}>{device}</span>
          <span className={`pill ${model.useRecommended ? "pill-auto" : "pill-manual"}`}>
            {model.useRecommended ? "Auto-tuned" : "Manual"}
          </span>
          {validation && (
            <span className={`pill ${validation.valid ? "pill-ok" : "pill-err"}`}>
              {validation.valid ? "Valid" : `${validation.errors.length} errors`}
            </span>
          )}
        </div>
      </header>

      <div className="dash-grid">
        <MetricCard
          label="Rollout buffer"
          value={String(rollout)}
          sub={`${p.nSteps} × ${par.numEnvs} envs`}
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
          sub={`~${updates.toLocaleString()} updates`}
        />
        <MetricCard
          label="Parallel"
          value={String(par.numEnvs)}
          sub={parallelSummary(par)}
        />
      </div>

      {( !batchOk || (validation && !validation.valid) ) && (
        <div className="alert-stack">
          {!batchOk && (
            <div className="alert alert-warn" role="status">
              Rollout {rollout} is not divisible by batch_size {p.batchSize}.
            </div>
          )}
          {validation && !validation.valid && (
            <div className="alert alert-err" role="alert">
              {validation.errors[0]?.message}
              {validation.errors.length > 1 && ` (+${validation.errors.length - 1} more)`}
            </div>
          )}
        </div>
      )}

      <div className="dash-columns">
        <section className="dash-card">
          <h3>Output &amp; artifacts</h3>
          <dl className="dash-dl">
            <div>
              <dt>Config export</dt>
              <dd>
                <ul className="dash-export-list">
                  {exportNames.map((n) => (
                    <li key={n} className="mono">
                      exports/{n}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
            <div>
              <dt>Checkpoints</dt>
              <dd>{checkpointSummary(model.checkpoint)}</dd>
            </div>
            <div>
              <dt>Best model</dt>
              <dd>{bestModelSummary(model.bestModel)}</dd>
            </div>
            <div>
              <dt>Export formats</dt>
              <dd>{exportFormatsSummary(model.exportFormat.formats)}</dd>
            </div>
          </dl>
        </section>

        <section className="dash-card">
          <h3>Hyperparameter snapshot</h3>
          <dl className="dash-dl dash-dl-compact">
            <div>
              <dt>learning_rate</dt>
              <dd className="mono">{p.learningRate}</dd>
            </div>
            <div>
              <dt>n_steps / batch / epochs</dt>
              <dd className="mono">
                {p.nSteps} / {p.batchSize} / {p.nEpochs}
              </dd>
            </div>
            <div>
              <dt>γ / λ / clip</dt>
              <dd className="mono">
                {p.gamma} / {p.gaeLambda} / {p.clipRange}
              </dd>
            </div>
          </dl>
        </section>
      </div>

      {model.recommendationNotes.length > 0 && (
        <section className="dash-card dash-insights">
          <h3>Machine recommendations</h3>
          <ul className="insight-list">
            {model.recommendationNotes.slice(0, 6).map((n, i) => (
              <li key={i}>{n}</li>
            ))}
            {model.recommendationNotes.length > 6 && (
              <li className="insight-more">+{model.recommendationNotes.length - 6} more notes</li>
            )}
          </ul>
        </section>
      )}
    </div>
  );
}
