import { useTrainerStore } from "../../stores/trainerStore";
import { MetricCard } from "../../components/MetricCard";
import { enabledRewardCount, formatTimesteps, machineTier } from "../../utils/trainerMetrics";

export function OverviewPanel() {
  const model = useTrainerStore((s) => s.model);
  const validation = useTrainerStore((s) => s.validation);

  if (!model) {
    return (
      <div className="overview-panel empty">
        <div className="hero-card">
          <h1>RL Trainer</h1>
          <p className="hero-lead">
            Configure rewards, termination thresholds, curriculum stages, and custom parameters for
            your quadruped SB3 + ROS 2 / Gazebo run. Tune PPO hyperparameters and parallel envs in
            PPO Planner.
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
              <span>Configure task → Validate → Export YAML</span>
            </li>
            <li>
              <span className="step-num">4</span>
              <span>Export PPO config from PPO Planner for hyperparams & parallel envs</span>
            </li>
          </ol>
        </div>
        <p className="overview-footnote">
          Export writes <code>exports/rl_&lt;project&gt;_config.yaml</code> for your training stack.
        </p>
      </div>
    );
  }

  const curriculumTotal =
    model.curriculum.enabled && model.curriculum.stages.length > 0
      ? model.curriculum.stages.reduce((sum, s) => sum + s.timesteps, 0)
      : null;
  const tier = model.machineProfile ? machineTier(model.machineProfile.ramGb) : null;

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
            · task config
          </p>
        </div>
        <div className="overview-badges">
          {model.machineProfile && (
            <span className={`badge badge-device badge-${model.machineProfile.gpuAvailable ? "cuda" : "cpu"}`}>
              {model.machineProfile.gpuAvailable ? "GPU" : "CPU"}
            </span>
          )}
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
          label="Curriculum stages"
          value={model.curriculum.enabled ? String(model.curriculum.stages.length) : "—"}
          sub={
            model.curriculum.enabled
              ? `${model.curriculum.name || model.curriculum.curriculumId || "enabled"} · ${model.curriculum.terrainProfile ?? "flat"}`
              : "single-stage"
          }
        />
        <MetricCard
          label="Training steps"
          value={curriculumTotal != null ? formatTimesteps(curriculumTotal) : "—"}
          sub={curriculumTotal != null ? "curriculum total" : "set in PPO Planner"}
        />
        <MetricCard
          label="Host tier"
          value={tier ? tier.charAt(0).toUpperCase() + tier.slice(1) : "—"}
          sub={model.machineProfile ? `${model.machineProfile.ramGb.toFixed(0)} GB RAM` : "profile host"}
        />
      </div>

      {validation?.warnings.some((w) => w.code === "missing_ppo_config") && (
        <div className="banner banner-warn" role="status">
          Export <code>ppo_{model.projectName}_config.yaml</code> from PPO Planner before training.
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
                    · {s.gaitTypeId} · {(s.command?.targetLinVelX ?? s.targetLinVelX).toFixed(1)} m/s ·{" "}
                    {s.timesteps.toLocaleString()} steps
                  </span>
                </li>
              ))}
          </ol>
        </section>
      )}

      {model.recommendationNotes.length > 0 && (
        <section className="insight-card">
          <h3>Notes</h3>
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
            <code>rl_{model.projectName}_config.yaml</code> — task, curriculum, env refs
          </li>
          <li>
            <code>ppo_{model.projectName}_config.yaml</code> — from PPO Planner (hyperparams, parallel)
          </li>
        </ul>
      </section>
    </div>
  );
}
