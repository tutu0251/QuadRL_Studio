import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import { ActionButton } from "../../components/ActionButton";
import { useCommandPreview } from "../../hooks/useCommandPreview";
import { useMonitorStore } from "../../stores/monitorStore";
import type { SpawnConfig, SpawnOffset } from "../../types";

type Props = {
  project: string | null;
  busy: boolean;
  onBusy: (v: boolean) => void;
  onError: (msg: string | null) => void;
};

const EMPTY_OFFSET: SpawnOffset = { dx: 0, dy: 0, dz: 0, droll: 0, dpitch: 0, dyaw: 0 };

export function SpawnMonitorPage({ project, busy, onBusy, onError }: Props) {
  const spawnConfig = useMonitorStore((s) => s.spawnConfig);
  const setSpawnConfig = useMonitorStore((s) => s.setSpawnConfig);
  const [offset, setOffset] = useState<SpawnOffset>(EMPTY_OFFSET);
  const [delay, setDelay] = useState(25);

  const saveParams = useMemo(
    () => ({ body: { spawn_offset: offset, controller_apply_delay_s: delay } }),
    [offset, delay]
  );
  const confirmParams = useMemo(() => ({ body: { pose_confirmed: true } }), []);

  const savePreview = useCommandPreview(project, "spawn_config_save", saveParams);
  const confirmPreview = useCommandPreview(project, "spawn_config_confirm", confirmParams);

  const refresh = async () => {
    if (!project) return;
    const cfg = await api.getSpawnConfig(project);
    setSpawnConfig(cfg);
    setOffset(cfg.spawn_offset);
    setDelay(cfg.controller_apply_delay_s);
  };

  useEffect(() => {
    refresh().catch((e) => onError(String(e)));
  }, [project]);

  const save = async () => {
    if (!project) return;
    onBusy(true);
    onError(null);
    try {
      const r = await api.patchSpawnConfig(project, {
        spawn_offset: offset,
        controller_apply_delay_s: delay,
      });
      setSpawnConfig(r);
      savePreview.refresh();
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const confirmPose = async () => {
    if (!project) return;
    onBusy(true);
    onError(null);
    try {
      const r = await api.patchSpawnConfig(project, { pose_confirmed: true });
      setSpawnConfig(r);
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const cfg = spawnConfig;
  const disabled = !project || busy;

  return (
    <div className="page-grid spawn-page">
      <section className="panel">
        <header className="panel-header">
          <div>
            <h2>Geometry Spawn Export</h2>
            <p className="panel-subtitle">Exported spawn pose and joint angles used to place the robot.</p>
          </div>
          {cfg && (
            <span className={`badge ${cfg.pose_confirmed ? "badge-completed" : "badge-stopped"}`}>
              {cfg.pose_confirmed ? "confirmed" : "unconfirmed"}
            </span>
          )}
        </header>
        {!project && <p className="panel-hint">Load a project to review spawn pose.</p>}
        {cfg?.missing_export && (
          <p className="panel-warn">Missing {cfg.export_path} — export from Geometry Editor first.</p>
        )}
        {cfg && (
          <>
            <p className="panel-hint">
              Pose: <strong>{cfg.pose_name}</strong> · file: <span className="mono">{cfg.export_path}</span>
            </p>
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>Joint</th>
                  <th>Angle (rad)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(cfg.joints).map(([name, val]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td className="mono">{val.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="btn-row">
              <ActionButton
                className="btn primary"
                disabled={disabled || cfg.pose_confirmed}
                command={confirmPreview.preview?.command}
                commandLoading={confirmPreview.loading}
                onClick={() => void confirmPose()}
              >
                Confirm spawn export
              </ActionButton>
            </div>
          </>
        )}
      </section>

      <section className="panel">
        <header className="panel-header">
          <div>
            <h2>Spawn Offset</h2>
            <p className="panel-subtitle">Applied on top of base spawn; saved to effective spawn in export YAML.</p>
          </div>
        </header>
        <div className="form-grid">
          {(["dx", "dy", "dz", "droll", "dpitch", "dyaw"] as const).map((key) => (
            <label key={key} className="field-row">
              <span>{key}</span>
              <input
                type="number"
                step="0.01"
                disabled={disabled}
                value={offset[key]}
                onChange={(e) => setOffset((o) => ({ ...o, [key]: parseFloat(e.target.value) || 0 }))}
              />
            </label>
          ))}
        </div>
        {cfg && (
          <dl className="status-grid">
            <dt>Effective spawn</dt>
            <dd className="mono">
              x={cfg.effective_spawn.x?.toFixed(3)} y={cfg.effective_spawn.y?.toFixed(3)} z=
              {cfg.effective_spawn.z?.toFixed(3)}
            </dd>
          </dl>
        )}
      </section>

      <section className="panel">
        <header className="panel-header">
          <div>
            <h2>Controller Warmup</h2>
            <p className="panel-subtitle">
              Delay after spawn before control applies (controller_apply_delay_s; training uses QUADRL_SIM_WARMUP_S).
            </p>
          </div>
        </header>
        <label className="field-row">
          <span>Apply delay (s)</span>
          <input
            type="number"
            min={0}
            step={1}
            disabled={disabled}
            value={delay}
            onChange={(e) => setDelay(parseFloat(e.target.value) || 0)}
          />
        </label>
        <div className="btn-row">
          <ActionButton
            className="btn primary"
            disabled={disabled}
            command={savePreview.preview?.command}
            commandLoading={savePreview.loading}
            onClick={() => void save()}
          >
            Save spawn settings
          </ActionButton>
        </div>
      </section>
    </div>
  );
}

function renderYamlPreview(cfg: SpawnConfig | null) {
  if (!cfg) return "Load a project…";
  return JSON.stringify(
    { spawn: cfg.effective_spawn, joints: cfg.joints, timing: { controller_apply_delay_s: cfg.controller_apply_delay_s } },
    null,
    2
  );
}

export function SpawnYamlPreview() {
  const cfg = useMonitorStore((s) => s.spawnConfig);
  return <pre className="export-preview">{renderYamlPreview(cfg)}</pre>;
}
