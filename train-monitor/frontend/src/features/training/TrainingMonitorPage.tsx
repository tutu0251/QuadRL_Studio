import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import { ActionButton } from "../../components/ActionButton";
import { NumericInput } from "../../components/NumericInput";
import { ResizableColumns } from "../../components/ResizableColumns";
import { useCommandPreview } from "../../hooks/useCommandPreview";
import { useMonitorStore } from "../../stores/monitorStore";
import type { ActionScaleEntry, ObservationScaleEntry, TrainStatus } from "../../types";

type Props = {
  project: string | null;
  trainStatus: TrainStatus | null;
  busy: boolean;
  onBusy: (v: boolean) => void;
  onError: (msg: string | null) => void;
};

export function TrainingMonitorPage({ project, trainStatus, busy, onBusy, onError }: Props) {
  const trainingConfig = useMonitorStore((s) => s.trainingConfig);
  const setTrainingConfig = useMonitorStore((s) => s.setTrainingConfig);

  const [actionScales, setActionScales] = useState<ActionScaleEntry[]>([]);
  const [obsScales, setObsScales] = useState<ObservationScaleEntry[]>([]);

  const saveBody = useMemo(
    () => ({ body: { action_scales: actionScales, observation_scales: obsScales } }),
    [actionScales, obsScales]
  );
  const savePreview = useCommandPreview(project, "training_config_save", saveBody);

  const refresh = async () => {
    if (!project) return;
    const cfg = await api.getTrainingConfig(project);
    setTrainingConfig(cfg);
    setActionScales(cfg.action_scales);
    setObsScales(cfg.observation_scales);
  };

  useEffect(() => {
    refresh().catch((e) => onError(String(e)));
  }, [project]);

  const save = async () => {
    if (!project) return;
    onBusy(true);
    onError(null);
    try {
      const r = await api.patchTrainingConfig(project, {
        action_scales: actionScales,
        observation_scales: obsScales,
      });
      setTrainingConfig(r);
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const disabled = !project || busy;
  const cfg = trainingConfig;

  return (
    <div className="page-grid training-page">
      <section className="panel train-summary-panel">
        <header className="panel-header">
          <div>
            <h2>Training Progress</h2>
            <p className="panel-subtitle">
              Live status from the training process — start/stop in Metric Monitor; full logs in the console.
            </p>
          </div>
        </header>
        <div className="stat-row">
          <div className="stat-card accent">
            <span className="stat-card-label">Stage</span>
            <span className="stat-card-value">{trainStatus?.current_stage ?? "—"}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card-label">Steps</span>
            <span className="stat-card-value">{trainStatus?.progress_message ?? "—"}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card-label">Rollouts</span>
            <span className="stat-card-value">{trainStatus?.rollout_count ?? "—"}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card-label">Episodes</span>
            <span className="stat-card-value">{trainStatus?.episode_count ?? "—"}</span>
          </div>
          {trainStatus?.last_termination_reason && (
            <div className="stat-card warn">
              <span className="stat-card-label">Last termination</span>
              <span className="stat-card-value">{trainStatus.last_termination_reason}</span>
            </div>
          )}
        </div>
      </section>

      <ResizableColumns storageKey="quadrl.trainMonitor.trainingCols">
      <section className="panel">
        <header className="panel-header">
          <h2>Action Scale</h2>
          <span className="panel-hint mono">{cfg?.gains_path}</span>
        </header>
        {!project && <p className="panel-hint">Load a project.</p>}
        {actionScales.length > 0 && (
          <table className="data-table compact">
            <thead>
              <tr>
                <th>Joint</th>
                <th>Default pos</th>
                <th>Action scale</th>
              </tr>
            </thead>
            <tbody>
              {actionScales.map((row, i) => (
                <tr key={row.joint}>
                  <td>{row.joint}</td>
                  <td className="mono">{row.default_position.toFixed(4)}</td>
                  <td>
                    <NumericInput
                      step={0.01}
                      disabled={disabled}
                      value={row.action_scale}
                      onCommit={(v) => {
                        setActionScales((rows) => rows.map((r, j) => (j === i ? { ...r, action_scale: v ?? 0 } : r)));
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel obs-scales-panel">
        <header className="panel-header">
          <h2>Observation Scales</h2>
          <span className="panel-hint mono">{cfg?.rl_config_path}</span>
        </header>
        {obsScales.length > 0 && (
          <div className="table-wrap">
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Topic</th>
                  <th>Scale</th>
                  <th>Offset</th>
                  <th>Clip min</th>
                  <th>Clip max</th>
                </tr>
              </thead>
              <tbody>
                {obsScales.map((row, i) => (
                  <tr key={row.id}>
                    <td>{row.key}</td>
                    <td className="mono">{row.topic}</td>
                    <td>
                      <NumericInput
                        step={0.01}
                        disabled={disabled}
                        value={row.scale}
                        onCommit={(v) => {
                          setObsScales((rows) => rows.map((r, j) => (j === i ? { ...r, scale: v ?? 0 } : r)));
                        }}
                      />
                    </td>
                    <td>
                      <NumericInput
                        step={0.01}
                        disabled={disabled}
                        value={row.offset}
                        onCommit={(v) => {
                          setObsScales((rows) => rows.map((r, j) => (j === i ? { ...r, offset: v ?? 0 } : r)));
                        }}
                      />
                    </td>
                    <td>
                      <NumericInput
                        step={0.01}
                        nullable
                        disabled={disabled}
                        value={row.clip_min ?? null}
                        onCommit={(v) => {
                          setObsScales((rows) => rows.map((r, j) => (j === i ? { ...r, clip_min: v } : r)));
                        }}
                      />
                    </td>
                    <td>
                      <NumericInput
                        step={0.01}
                        nullable
                        disabled={disabled}
                        value={row.clip_max ?? null}
                        onCommit={(v) => {
                          setObsScales((rows) => rows.map((r, j) => (j === i ? { ...r, clip_max: v } : r)));
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="btn-row">
          <ActionButton
            className="btn primary"
            disabled={disabled}
            command={savePreview.preview?.command}
            commandLoading={savePreview.loading}
            onClick={() => void save()}
          >
            Save scales to exports
          </ActionButton>
        </div>
      </section>

      <section className="panel">
        <header className="panel-header">
          <h2>Termination</h2>
          {cfg?.curriculum_enabled && <span className="badge badge-running">curriculum</span>}
        </header>
        {(cfg?.terminations ?? []).map((t) => (
          <div key={t.stage_name ?? "base"} className="termination-block">
            <h3>{t.stage_name ?? "Base task"}</h3>
            <ul className="workspace-stats mono">
              <li>max_episode_steps: {t.max_episode_steps}</li>
              <li>fall_base_height_threshold: {t.fall_base_height_threshold}</li>
              <li>max_tilt_rad: {t.max_tilt_rad}</li>
              <li>enabled terms: {t.enabled_term_ids.join(", ") || "—"}</li>
            </ul>
          </div>
        ))}
      </section>
      </ResizableColumns>
    </div>
  );
}
