import { useTrainerStore } from "../../stores/trainerStore";
import { MetricCard } from "../../components/MetricCard";
import {
  batchDividesRollout,
  enabledRewardCount,
  formatTimesteps,
  resolvedDevice,
  rolloutSize,
} from "../../utils/trainerMetrics";

export function OverviewPanel() {
  const model = useTrainerStore((s) => s.model);
  const validation = useTrainerStore((s) => s.validation);

  if (!model) {
    return (
      <div className="overview-panel empty">
        <div className="hero-card">
          <h1>RL Trainer</h1>
          <p className="hero-lead">
            Configure rewards, termination thresholds, PPO hyperparameters, and parallel training
            for your quadruped SB3 + ROS 2 / Gazebo run.
          </p>
        </div>
        <div className="workflow-card">
          <h2>Workflow</h2>
          <ol className="workflow-steps">
            <li>
              <span className="step-num">1</span>
              <span>Complete sensor RL export (observations + bridge)</span>
            </li>
            <li>
              <span className="step-num">2</span>
              <span>File → select project (bootstraps velocity tracking preset)</span>
            </li>
            <li>
              <span className="step-num">3</span>
              <span>Recommend → Validate → Export YAML</span>
            </li>
          </ol>
        </div>
        <p className="overview-footnote">
          Export writes <code>exports/rl_&lt;project&gt;_config.yaml</code> for your training stack.
        </p>
      </div>
    );
  }

  const p = model.hyperparams;
  const par = model.parallel;
  const rollout = rolloutSize(p, par.numEnvs);
  const batchOk = batchDividesRollout(p, par.numEnvs);
  const device = resolvedDevice(p, model.machineProfile);

  return (
    <div className="overview-panel">
      <header className="overview-header">
        <div>
          <h2>{model.robotName}</h2>
          <p className="overview-subtitle">
            Project <span className="mono">{model.projectName}</span> ·{" "}
            {model.curriculum.enabled
              ? `curriculum: ${model.curriculum.name || model.curriculum.curriculumId}`
              : model.selectedPresetId ?? "no preset"}{" "}
            · PPO / SB3
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
          label="Reward terms"
          value={String(enabledRewardCount(model))}
          sub={`${model.rewardTerms.length} defined`}
          variant="accent"
        />
        <MetricCard
          label="Rollout buffer"
          value={String(rollout)}
          sub={`${p.nSteps} × ${par.numEnvs} envs`}
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
          sub={`${par.vecEnvType} vec env`}
        />
      </div>

      {!batchOk && (
        <div className="banner banner-warn" role="status">
          Rollout size ({rollout}) is not divisible by batch_size ({p.batchSize}).
        </div>
      )}

      {model.curriculum.enabled && model.curriculum.stages.length > 0 && (
        <section className="insight-card">
          <h3>Progressive training</h3>
          <ol className="curriculum-pipeline compact">
            {[...model.curriculum.stages]
              .sort((a, b) => a.order - b.order)
              .map((s, i) => (
                <li
                  key={s.id}
                  className={i === model.curriculum.currentStageIndex ? "current" : ""}
                >
                  <strong>{s.name}</strong>
                  <span className="mono">
                    {" "}
                    · {s.targetLinVelX} m/s · {s.timesteps.toLocaleString()} steps
                  </span>
                </li>
              ))}
          </ol>
        </section>
      )}

      {model.recommendationNotes.length > 0 && (
        <section className="insight-card">
          <h3>Recommendations</h3>
          <ul className="insight-list">
            {model.recommendationNotes.slice(-6).map((n, i) => (
              <li key={i}>
                <span className="insight-dot" aria-hidden />
                {n}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="export-hints">
        <p className="export-hints-title">On export</p>
        <ul>
          <li>
            <code>rl_{model.projectName}_config.yaml</code>
          </li>
        </ul>
      </section>
    </div>
  );
}
