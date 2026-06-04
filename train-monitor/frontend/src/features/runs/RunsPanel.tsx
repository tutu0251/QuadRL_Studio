import { formatTimestamp } from "../../utils/format";
import type { RunInfo } from "../../types";

type Props = {
  runs: RunInfo[];
  selectedRunId: string | null;
  selectedStageLogdir?: string | null;
  onSelect: (runId: string) => void;
  onSelectStage?: (logdir: string | null) => void;
};

const STATUS_CLASS: Record<string, string> = {
  running: "badge-running",
  completed: "badge-completed",
  failed: "badge-failed",
  stopped: "badge-stopped",
  unknown: "badge-unknown",
};

export function RunsPanel({ runs, selectedRunId, selectedStageLogdir, onSelect, onSelectStage }: Props) {
  const selectedRun = runs.find((r) => r.run_id === selectedRunId);

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Runs</h2>
        <span className="panel-count">{runs.length}</span>
      </header>
      {runs.length === 0 ? (
        <p className="panel-hint">No TensorBoard runs yet.</p>
      ) : (
        <>
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
                    {run.started_at && ` · ${formatTimestamp(run.started_at)}`}
                    {run.curriculum_enabled && " · curriculum"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {selectedRun && selectedRun.stages.length > 0 && onSelectStage && (
            <div className="stage-select">
              <h3>Stage charts</h3>
              <ul className="item-list compact">
                <li>
                  <button
                    type="button"
                    className={`list-btn ${!selectedStageLogdir ? "selected" : ""}`}
                    onClick={() => onSelectStage(null)}
                  >
                    All stages
                  </button>
                </li>
                {selectedRun.stages.map((stage) => (
                  <li key={stage.logdir}>
                    <button
                      type="button"
                      className={`list-btn ${selectedStageLogdir === stage.logdir ? "selected" : ""}`}
                      onClick={() => onSelectStage(stage.logdir)}
                    >
                      <span className="list-title">{stage.name}</span>
                      {!stage.has_events && <span className="list-meta">no events</span>}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
