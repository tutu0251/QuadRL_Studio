import type { RunInfo } from "../../types";

type Props = {
  runs: RunInfo[];
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
};

const STATUS_CLASS: Record<string, string> = {
  running: "badge-running",
  completed: "badge-completed",
  failed: "badge-failed",
  stopped: "badge-stopped",
  unknown: "badge-unknown",
};

export function RunsPanel({ runs, selectedRunId, onSelect }: Props) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Runs</h2>
        <span className="panel-count">{runs.length}</span>
      </header>
      {runs.length === 0 ? (
        <p className="panel-hint">No TensorBoard runs yet.</p>
      ) : (
        <ul className="item-list">
          {runs.map((run) => (
            <li key={run.run_id}>
              <button
                type="button"
                className={`list-btn ${selectedRunId === run.run_id ? "selected" : ""}`}
                onClick={() => onSelect(run.run_id)}
              >
                <span className="list-title">{run.run_id}</span>
                <span className="list-meta">
                  <span className={`badge ${STATUS_CLASS[run.status] ?? "badge-unknown"}`}>{run.status}</span>
                  {run.started_at && ` · ${run.started_at}`}
                  {run.curriculum_enabled && " · curriculum"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
