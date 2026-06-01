import type { ExportBundle } from "../../types";

const CATEGORY_LABELS: Record<string, string> = {
  geometry: "Geometry",
  physics: "Physics",
  control: "Control",
  sensor: "Sensor",
  ppo_planner: "PPO Planner",
  rl_trainer: "RL Trainer",
  other: "Other",
};

type Props = {
  bundle: ExportBundle | null;
  selectedPath: string | null;
  preview: string | null;
  onSelect: (path: string) => void;
};

export function ExportsPanel({ bundle, selectedPath, preview, onSelect }: Props) {
  if (!bundle) {
    return (
      <section className="panel exports-panel">
        <header className="panel-header">
          <h2>Editor Exports</h2>
        </header>
        <p className="panel-hint">Load a project to browse export files.</p>
      </section>
    );
  }

  const byCategory = bundle.files.reduce<Record<string, typeof bundle.files>>((acc, file) => {
    (acc[file.category] ??= []).push(file);
    return acc;
  }, {});

  return (
    <section className="panel exports-panel">
      <header className="panel-header">
        <h2>Editor Exports</h2>
        <span className={`badge ${bundle.ready_for_training ? "badge-completed" : "badge-stopped"}`}>
          {bundle.ready_for_training ? "ready" : "incomplete"}
        </span>
      </header>

      {bundle.missing_required.length > 0 && (
        <p className="panel-warn">Missing: {bundle.missing_required.join(", ")}</p>
      )}

      <p className="panel-hint">
        Sim: {bundle.recommended_sim_backend ?? "mock"}
        {bundle.workspace_ready ? " · workspace built" : " · workspace not built"}
        {!bundle.sensor_exports_ready && " · sensor/control exports incomplete"}
      </p>

      <div className="exports-layout">
        <div className="exports-list">
          {Object.entries(byCategory).map(([category, files]) => (
            <div key={category} className="export-group">
              <h3>{CATEGORY_LABELS[category] ?? category}</h3>
              <ul className="item-list compact">
                {files.map((file) => (
                  <li key={file.path}>
                    <button
                      type="button"
                      className={`list-btn ${selectedPath === file.path ? "selected" : ""}`}
                      onClick={() => onSelect(file.path)}
                    >
                      <span className="list-title">{file.filename}</span>
                      <span className="list-meta">{file.format.toUpperCase()}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <pre className="export-preview">{preview ?? "Select a file to preview"}</pre>
      </div>
    </section>
  );
}
