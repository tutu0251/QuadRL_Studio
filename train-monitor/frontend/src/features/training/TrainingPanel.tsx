import { useEffect, useState } from "react";
import { formatElapsedSince, formatTimestamp } from "../../utils/format";
import { ActionButton } from "../../components/ActionButton";
import { useCommandPreview } from "../../hooks/useCommandPreview";
import type { StageInfo, TrainStatus } from "../../types";

type Props = {
  project: string | null;
  status: TrainStatus | null;
  ready: boolean;
  selectedCheckpoint: string | null;
  stages: StageInfo[];
  gazeboHeadless: boolean;
  guiAvailable: boolean;
  resolvedDisplay: string | null;
  resetLogStd: boolean;
  onGazeboHeadlessChange: (v: boolean) => void;
  onResetLogStdChange: (v: boolean) => void;
  onStart: () => void;
  onStop: () => void;
  onResume: () => void;
  onStartFromStage: (stageIndex: number) => void;
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
  stages,
  gazeboHeadless,
  guiAvailable,
  resolvedDisplay,
  resetLogStd,
  onGazeboHeadlessChange,
  onResetLogStdChange,
  onStart,
  onStop,
  onResume,
  onStartFromStage,
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
  const hasStages = stages.length > 0;
  const [stageIndex, setStageIndex] = useState(0);

  // Keep the selected stage in range as the curriculum (project) changes.
  useEffect(() => {
    setStageIndex((i) => (i < stages.length ? i : 0));
  }, [stages.length]);

  const canStartFromStage = Boolean(project && ready && selectedCheckpoint && hasStages);
  const startStagePreview = useCommandPreview(
    project,
    "train_resume",
    {
      gazebo_headless: gazeboHeadless,
      resume_checkpoint: selectedCheckpoint ?? "",
      start_stage: stageIndex,
      reset_log_std: resetLogStd,
    },
    canStartFromStage
  );

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
        <label
          className="checkbox-row train-reset-logstd"
          title="On Continue / Start-from-stage, reset the policy's action log_std to the PPO config's log_std_init so exploration is restored. Does not affect a fresh Start."
        >
          <input
            type="checkbox"
            checked={resetLogStd}
            disabled={running || busy}
            onChange={(e) => onResetLogStdChange(e.target.checked)}
          />
          Reset exploration (log_std) on resume
        </label>
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
            title={selectedCheckpoint ? `Continue from ${selectedCheckpoint}` : "Select a checkpoint"}
          >
            {selectedCheckpoint ? "Continue from checkpoint" : "Continue (select checkpoint)"}
          </ActionButton>
        </div>

        {hasStages && (
          <div className="train-stage-resume">
            <label className="train-stage-label" htmlFor="train-start-stage">
              Start from stage
            </label>
            <div className="train-stage-row">
              <select
                id="train-start-stage"
                className="train-stage-select"
                value={stageIndex}
                disabled={running || busy}
                onChange={(e) => setStageIndex(Number(e.target.value))}
              >
                {stages.map((stage, i) => (
                  <option key={stage.id} value={i}>
                    {`Stage ${i + 1}: ${stage.name}`}
                  </option>
                ))}
              </select>
              <ActionButton
                className="btn ghost"
                disabled={!canStartFromStage || running || busy}
                command={startStagePreview.preview?.command}
                commandLoading={startStagePreview.loading}
                onClick={() => onStartFromStage(stageIndex)}
                title={
                  selectedCheckpoint
                    ? `Restart ${stages[stageIndex]?.name ?? `stage ${stageIndex + 1}`} seeded with ${selectedCheckpoint}`
                    : "Select a checkpoint to seed the stage"
                }
              >
                Start from stage
              </ActionButton>
            </div>
          </div>
        )}
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
