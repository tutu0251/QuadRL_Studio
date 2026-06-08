import { useEffect, useState } from "react";
import { formatElapsedSince, formatTimestamp } from "../../utils/format";
import { ActionButton } from "../../components/ActionButton";
import type { TrainStatus } from "../../types";

type Props = {
  project: string | null;
  status: TrainStatus | null;
  ready: boolean;
  selectedCheckpoint: string | null;
  gazeboHeadless: boolean;
  guiAvailable: boolean;
  resolvedDisplay: string | null;
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
  gazeboHeadless,
  guiAvailable,
  resolvedDisplay,
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

  const hasActivity = Boolean(status?.current_stage || status?.progress_message);
  const hasCounters = status?.rollout_count != null || status?.episode_count != null;

  return (
    <section className="panel training-panel">
      <header className="panel-header">
        <h2>
          <span className={`live-dot${running ? " on" : ""}`} aria-hidden="true" />
          Training
        </h2>
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

      {hasActivity && (
        <div className="train-activity" aria-live="polite">
          {status?.current_stage && (
            <span className="train-activity-stage">{status.current_stage}</span>
          )}
          {status?.progress_message && (
            <span className="train-activity-progress mono">{status.progress_message}</span>
          )}
        </div>
      )}

      {hasCounters && (
        <div className="train-metrics">
          <div className="train-metric">
            <span className="train-metric-value mono">{status?.rollout_count ?? "—"}</span>
            <span className="train-metric-label">Rollouts</span>
          </div>
          <div className="train-metric">
            <span className="train-metric-value mono">{status?.episode_count ?? "—"}</span>
            <span className="train-metric-label">Episodes</span>
          </div>
        </div>
      )}

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
        <div className="train-action-grid">
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
            className="btn ghost train-action-resume"
            disabled={!project || !ready || !selectedCheckpoint || running || busy}
            command={resumeCommand}
            commandLoading={resumeCommandLoading}
            onClick={onResume}
            title={selectedCheckpoint ? `Resume from ${selectedCheckpoint}` : "Select a checkpoint"}
          >
            {selectedCheckpoint ? "Resume from checkpoint" : "Resume (select checkpoint)"}
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
          {status.last_termination_reason && (
            <>
              <dt>Last termination</dt>
              <dd>{status.last_termination_reason}</dd>
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
