import { useEffect, useState } from "react";
import { formatElapsedSince, formatTimestamp } from "../../utils/format";
import type { TrainStatus } from "../../types";

type Props = {
  project: string | null;
  status: TrainStatus | null;
  ready: boolean;
  selectedCheckpoint: string | null;
  dryRun: boolean;
  gazeboHeadless: boolean;
  recommendedSim: string;
  onDryRunChange: (v: boolean) => void;
  onGazeboHeadlessChange: (v: boolean) => void;
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
  gazeboHeadless,
  recommendedSim,
  onDryRunChange,
  onGazeboHeadlessChange,
  onStart,
  onStop,
  onResume,
  busy,
}: Props) {
  const running = status?.state === "running" || status?.state === "starting";
  const stateLabel = status?.state ?? "idle";
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!running || !status?.started_at) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [running, status?.started_at]);

  const elapsed =
    running && status?.started_at ? formatElapsedSince(status.started_at, now) : null;

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

      {elapsed && (
        <div className="train-elapsed" aria-live="polite">
          <span className="train-elapsed-label">Elapsed</span>
          <span className="train-elapsed-value mono">{elapsed}</span>
          {status?.started_at && (
            <span className="train-elapsed-started">since {formatTimestamp(status.started_at)}</span>
          )}
        </div>
      )}

      <p className="panel-hint">
        Simulation: auto ({recommendedSim} when workspace and ROS are ready, otherwise mock)
      </p>

      <div className="train-controls">
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={gazeboHeadless}
            onChange={(e) => onGazeboHeadlessChange(e.target.checked)}
            disabled={running}
          />
          Headless Gazebo (no GUI — recommended for training servers)
        </label>
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
              <dd className="mono">{status.run_id}</dd>
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
