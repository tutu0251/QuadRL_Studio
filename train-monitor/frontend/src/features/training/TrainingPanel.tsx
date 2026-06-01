import type { TrainStatus } from "../../types";

type Props = {
  project: string | null;
  status: TrainStatus | null;
  ready: boolean;
  selectedCheckpoint: string | null;
  dryRun: boolean;
  onDryRunChange: (v: boolean) => void;
  onStart: () => void;
  onStop: () => void;
  onResume: () => void;
  busy: boolean;
};

export function TrainingPanel({
  project,
  status,
  ready,
  selectedCheckpoint,
  dryRun,
  onDryRunChange,
  onStart,
  onStop,
  onResume,
  busy,
}: Props) {
  const running = status?.state === "running" || status?.state === "starting";
  const stateLabel = status?.state ?? "idle";

  return (
    <section className="panel training-panel">
      <header className="panel-header">
        <h2>Training</h2>
        <span className={`badge badge-${stateLabel}`}>{stateLabel}</span>
      </header>

      {!project && <p className="panel-hint">Load a project to control training.</p>}

      {project && !ready && (
        <p className="panel-warn">
          Missing required exports (rl_* and ppo_* config YAML). Export from RL Trainer and PPO Planner first.
        </p>
      )}

      <div className="train-controls">
        <label className="checkbox-row">
          <input type="checkbox" checked={dryRun} onChange={(e) => onDryRunChange(e.target.checked)} />
          Dry run (no SB3)
        </label>
        <div className="btn-row">
          <button type="button" className="btn primary" disabled={!project || !ready || running || busy} onClick={onStart}>
            Start
          </button>
          <button type="button" className="btn danger" disabled={!running || busy} onClick={onStop}>
            Stop
          </button>
          <button
            type="button"
            className="btn"
            disabled={!project || !ready || !selectedCheckpoint || running || busy}
            onClick={onResume}
            title={selectedCheckpoint ? `Resume from ${selectedCheckpoint}` : "Select a checkpoint"}
          >
            Resume
          </button>
        </div>
      </div>

      {status && (
        <dl className="status-grid">
          {status.run_id && (
            <>
              <dt>Run</dt>
              <dd>{status.run_id}</dd>
            </>
          )}
          {status.current_stage && (
            <>
              <dt>Stage</dt>
              <dd>{status.current_stage}</dd>
            </>
          )}
          {status.progress_message && (
            <>
              <dt>Progress</dt>
              <dd>{status.progress_message}</dd>
            </>
          )}
          {status.pid && (
            <>
              <dt>PID</dt>
              <dd>{status.pid}</dd>
            </>
          )}
        </dl>
      )}
    </section>
  );
}
