import type { WorkspaceStatus } from "../../types";

type Props = {
  project: string | null;
  status: WorkspaceStatus | null;
  busy: boolean;
  onRefresh: () => void;
  onGenerate: () => void;
  onBuild: (clean: boolean) => void;
  onValidateExports: () => void;
  onValidate: (opts: { staticOnly: boolean; skipRuntime: boolean }) => void;
  onSetup: (opts: { staticOnly: boolean; skipRuntime: boolean }) => void;
};

export function WorkspacePanel({
  project,
  status,
  busy,
  onRefresh,
  onGenerate,
  onBuild,
  onValidateExports,
  onValidate,
  onSetup,
}: Props) {
  const running = status?.state === "running" || status?.state === "starting";
  const disabled = !project || busy || running;

  return (
    <section className="panel workspace-panel">
      <header className="panel-header">
        <h2>Workspace</h2>
        {status && (
          <span
            className={`badge ${status.training_ready ? "badge-completed" : status.build_ready ? "badge-running" : "badge-stopped"}`}
          >
            {status.training_ready ? "ready" : status.build_ready ? "built" : "not built"}
          </span>
        )}
      </header>

      {!project && <p className="panel-hint">Load a project to manage the colcon workspace.</p>}

      {project && status && (
        <>
          <ul className="workspace-stats mono">
            <li>
              Build: {status.build_ready ? "yes" : "no"}
              {status.exports_stale && " (exports stale)"}
            </li>
            <li>Readiness: {status.readiness_status ?? "—"}</li>
            <li>Sim: {status.recommended_sim_backend}</li>
            {status.operation && running && <li>Running: {status.operation}</li>}
            {status.error && <li className="panel-warn">{status.error}</li>}
          </ul>

          <div className="btn-row wrap">
            <button type="button" className="btn primary" disabled={disabled} onClick={() => onSetup({ staticOnly: false, skipRuntime: false })}>
              Full setup
            </button>
            <button type="button" className="btn" disabled={disabled} onClick={onGenerate}>
              Generate
            </button>
            <button type="button" className="btn" disabled={disabled} onClick={() => onBuild(false)}>
              Build
            </button>
            <button type="button" className="btn" disabled={disabled} onClick={() => onBuild(true)}>
              Clean build
            </button>
          </div>
          <div className="btn-row wrap">
            <button type="button" className="btn" disabled={disabled} onClick={onValidateExports}>
              Check exports
            </button>
            <button type="button" className="btn" disabled={disabled} onClick={() => onValidate({ staticOnly: true, skipRuntime: true })}>
              Static only
            </button>
            <button type="button" className="btn" disabled={disabled} onClick={() => onValidate({ staticOnly: false, skipRuntime: true })}>
              Validate (no Gazebo)
            </button>
            <button type="button" className="btn" disabled={!project || busy} onClick={onRefresh}>
              Refresh
            </button>
          </div>
          <p className="panel-hint">
            Full setup = generate workspace, colcon build, headless Gazebo readiness (same as setup_robot.sh).
          </p>
        </>
      )}
    </section>
  );
}
