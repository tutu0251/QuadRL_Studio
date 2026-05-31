import { useTrainerStore } from "../../stores/trainerStore";
import { formatTimesteps } from "../../utils/trainerMetrics";

export function OverviewPanel({ compact = false }: { compact?: boolean }) {
  const model = useTrainerStore((s) => s.model);
  const validation = useTrainerStore((s) => s.validation);

  if (!model) {
    return (
      <div className={`unity-panel overview-sidebar ${compact ? "compact" : ""}`}>
        <div className="panel-header panel-header-compact">
          <span>Summary</span>
        </div>
        <div className="panel-empty-state compact-empty">
          <p className="empty-desc">File → open a project to begin.</p>
          <ol className="workflow-steps compact-workflow">
            <li>Sensor export</li>
            <li>Select project</li>
            <li>Configure &amp; export YAML</li>
          </ol>
        </div>
      </div>
    );
  }

  const curriculumTotal =
    model.curriculum.enabled && model.curriculum.stages.length > 0
      ? model.curriculum.stages.reduce((sum, s) => sum + s.timesteps, 0)
      : null;

  const stages = model.curriculum.enabled
    ? [...model.curriculum.stages].sort((a, b) => a.order - b.order)
    : [];

  return (
    <div className={`unity-panel overview-sidebar ${compact ? "compact" : ""}`}>
      <div className="panel-header panel-header-compact">
        <span>Summary</span>
        {validation && (
          <span className={`panel-header-meta ${validation.valid ? "meta-ok" : "meta-warn"}`}>
            {validation.valid ? "OK" : `${validation.errors.length} err`}
          </span>
        )}
      </div>

      <div className="overview-sidebar-scroll">
        <div className="side-summary-block">
          <strong className="side-project-name">{model.robotName}</strong>
          <span className="mono side-project-id">{model.projectName}</span>
        </div>

        <dl className="side-stats">
          <div className="side-stat">
            <dt>Curriculum</dt>
            <dd>{model.curriculum.enabled ? model.curriculum.name || "enabled" : "off"}</dd>
          </div>
          <div className="side-stat">
            <dt>Stages</dt>
            <dd>{model.curriculum.enabled ? String(stages.length) : "—"}</dd>
          </div>
          <div className="side-stat">
            <dt>Terrain</dt>
            <dd>{model.curriculum.terrainProfile ?? "flat"}</dd>
          </div>
          <div className="side-stat">
            <dt>Steps</dt>
            <dd className="mono">{curriculumTotal != null ? formatTimesteps(curriculumTotal) : "—"}</dd>
          </div>
          <div className="side-stat">
            <dt>Gate types</dt>
            <dd>{model.gaitTypes?.length ?? 0}</dd>
          </div>
        </dl>

        {validation?.warnings.some((w) => w.code === "missing_ppo_config") && (
          <p className="side-hint warn">Export PPO config before training.</p>
        )}

        {stages.length > 0 && (
          <section className="side-stage-list">
            <h4 className="section-label">Pipeline</h4>
            <ol className="curriculum-pipeline compact">
              {stages.map((s, i) => (
                <li key={s.id} className={i === model.curriculum.currentStageIndex ? "current" : ""}>
                  <span className="side-stage-num">{i + 1}</span>
                  <span className="side-stage-name">{s.name}</span>
                </li>
              ))}
            </ol>
          </section>
        )}

        {model.recommendationNotes.length > 0 && (
          <section className="side-notes">
            <h4 className="section-label">Notes</h4>
            <ul className="insight-list compact">
              {model.recommendationNotes.slice(-3).map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
