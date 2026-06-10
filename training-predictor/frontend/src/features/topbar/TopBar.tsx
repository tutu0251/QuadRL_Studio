import { StatusBadge } from "../../components/StatusBadge";
import { isRunning, useStudyStore } from "../../stores/studyStore";

/** Top bar: brand, project picker, run controls, live study state, and backend health. */
export function TopBar({ onStart, onStop }: { onStart: () => void; onStop: () => void }) {
  const store = useStudyStore();
  const running = isRunning(store);
  const project = store.form.project;
  const state = store.status?.status ?? (store.taskId ? "running" : "idle");

  const advisorOk = store.health?.advisor_backend && store.health.advisor_backend !== "disabled";
  const monitorOk = store.health?.monitor_reachable;

  return (
    <header className="tp-topbar">
      <div className="tp-brand">
        <span className="tp-brand-mark" />
        <div className="tp-brand-text">
          <strong>Training Predictor</strong>
          <span>Optuna explores · Claude steers the search</span>
        </div>
      </div>

      <div className="tp-topbar-controls">
        <label className="tp-inline-field">
          <span className="qr-eyebrow">Project</span>
          <select
            className="tp-select"
            value={project}
            disabled={running || store.projects.length === 0}
            onChange={(e) => store.setProject(e.target.value)}
          >
            {store.projects.length === 0 ? (
              <option value="">No projects found</option>
            ) : (
              store.projects.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))
            )}
          </select>
        </label>

        {running ? (
          <button type="button" className="tp-btn tp-btn-danger" onClick={onStop}>
            Stop study
          </button>
        ) : (
          <button
            type="button"
            className="tp-btn tp-btn-primary"
            disabled={!project || !store.connected}
            onClick={onStart}
          >
            {store.form.study_name ? "Resume study" : "Start study"}
          </button>
        )}
      </div>

      <span className="tp-card-spacer" />

      <div className="tp-health">
        <span className={`tp-chip ${store.connected ? "ok" : "bad"}`} title={`API: ${store.health?.editor ?? "training-predictor"}`}>
          {store.connected ? "API connected" : "API offline"}
        </span>
        <span
          className={`tp-chip ${advisorOk ? "ok" : "warn"}`}
          title={store.health?.advisor_detail || "Set ANTHROPIC_API_KEY to enable Claude"}
        >
          {advisorOk ? `Claude: ${store.health?.advisor_backend}` : "Claude disabled"}
        </span>
        <span
          className={`tp-chip ${monitorOk ? "ok" : "warn"}`}
          title={store.health?.monitor_url ? `Train Monitor: ${store.health.monitor_url}` : "Train Monitor"}
        >
          {monitorOk ? "Monitor ready" : "Monitor offline"}
        </span>
      </div>

      <StatusBadge state={state} />
    </header>
  );
}
