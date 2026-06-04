import { useEffect, useState } from "react";
import { formatElapsedSince, formatTimestamp } from "../../utils/format";
import { ActionButton } from "../../components/ActionButton";
import type { TrainStatus } from "../../types";

type Props = {
  project: string | null;
  status: TrainStatus | null;
  ready: boolean;
  selectedCheckpoint: string | null;
  dryRun: boolean;
  gazeboHeadless: boolean;
  recommendedSim: string;
  guiAvailable: boolean;
  resolvedDisplay: string | null;
  onDryRunChange: (v: boolean) => void;
  onGazeboHeadlessChange: (v: boolean) => void;
  onStart: () => void;
  onStop: () => void;
  onResume: () => void;
  busy: boolean;
  startCommand?: string | null;
  stopCommand?: string | null;
  resumeCommand?: string | null;
  startCommandLoading?: boolean;
  stopCommandLoading?: boolean;
  resumeCommandLoading?: boolean;
};

export function TrainingPanel({
  project,
  status,
  ready,
  selectedCheckpoint,
  dryRun,
  gazeboHeadless,
  recommendedSim,
  guiAvailable,
  resolvedDisplay,
  onDryRunChange,
  onGazeboHeadlessChange,
  onStart,
  onStop,
  onResume,
  busy,
  startCommand,
  stopCommand,
  resumeCommand,
  startCommandLoading,
  stopCommandLoading,
  resumeCommandLoading,
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
        Simulation: ROS/Gazebo ({recommendedSim} when workspace and exports are ready). Metrics via
        TensorBoard below.
      </p>

      <div className="train-controls">
        <fieldset className="gazebo-mode-fieldset" disabled={running}>
          <legend className="gazebo-mode-legend">Gazebo</legend>
          <label className="radio-row">
            <input
              type="radio"
              name="gazebo-mode"
              checked={gazeboHeadless}
              onChange={() => onGazeboHeadlessChange(true)}
            />
            Headless
          </label>
          <label className="radio-row" title={guiAvailable ? undefined : "No X11 display on training host"}>
            <input
              type="radio"
              name="gazebo-mode"
              checked={!gazeboHeadless}
              disabled={!guiAvailable}
              onChange={() => onGazeboHeadlessChange(false)}
            />
            GUI (watch simulation)
          </label>
        </fieldset>
        {!guiAvailable && (
          <p className="panel-warn">
            No display on server — use Headless, or start VNC/desktop (set QUADRL_DISPLAY=:10).
          </p>
        )}
        {guiAvailable && resolvedDisplay && (
          <p className="panel-hint">GUI will use DISPLAY={resolvedDisplay}</p>
        )}
        <label className="checkbox-row">
          <input type="checkbox" checked={dryRun} onChange={(e) => onDryRunChange(e.target.checked)} />
          Dry run (no SB3)
        </label>
        <div className="btn-row train-action-row">
          <ActionButton
            className="btn primary"
            disabled={!project || !ready || running || busy}
            command={startCommand}
            commandLoading={startCommandLoading}
            onClick={onStart}
          >
            Start
          </ActionButton>
          <ActionButton
            className="btn danger"
            disabled={!running || busy}
            command={stopCommand}
            commandLoading={stopCommandLoading}
            onClick={onStop}
          >
            Stop
          </ActionButton>
          <ActionButton
            className="btn"
            disabled={!project || !ready || !selectedCheckpoint || running || busy}
            command={resumeCommand}
            commandLoading={resumeCommandLoading}
            onClick={onResume}
            title={selectedCheckpoint ? `Resume from ${selectedCheckpoint}` : "Select a checkpoint"}
          >
            Resume
          </ActionButton>
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
          {status.state !== "idle" && (
            <>
              <dt>Gazebo</dt>
              <dd>{status.gazebo_headless === false ? "GUI" : "Headless"}</dd>
            </>
          )}
        </dl>
      )}
    </section>
  );
}
