import { useEffect, useState } from "react";
import type { CheckpointInfo, TrainingCheckpointConfig } from "@rl-trainer-model";
import { api } from "../../api/client";

function formatSize(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`;
  return `${bytes} B`;
}

export function CheckpointSelector({
  project,
  config,
  onChange,
}: {
  project: string;
  config: TrainingCheckpointConfig;
  onChange: (patch: Partial<TrainingCheckpointConfig>) => void;
}) {
  const [checkpoints, setCheckpoints] = useState<CheckpointInfo[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = () => {
    setLoading(true);
    api
      .listCheckpoints(project)
      .then((r) => setCheckpoints(r.checkpoints))
      .catch(() => setCheckpoints([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, [project]);

  return (
    <div className="checkpoint-selector">
      <div className="checkpoint-header">
        <h4 className="section-label">Training checkpoint</h4>
        <button type="button" className="header-btn" onClick={refresh} disabled={loading}>
          {loading ? "Scanning…" : "Refresh"}
        </button>
      </div>
      <p className="panel-hint">
        Select a checkpoint to resume training, or leave as none to start from scratch.
      </p>
      <select
        className="param-input param-select checkpoint-select"
        value={config.resumeCheckpointPath ?? ""}
        onChange={(e) =>
          onChange({ resumeCheckpointPath: e.target.value || null })
        }
      >
        <option value="">None (train from scratch)</option>
        {checkpoints.map((c) => (
          <option key={c.path} value={c.path}>
            {c.filename} — {formatSize(c.sizeBytes)}
          </option>
        ))}
      </select>
      {config.resumeCheckpointPath && (
        <p className="stage-advance mono">Resume: {config.resumeCheckpointPath}</p>
      )}
      {checkpoints.length === 0 && !loading && (
        <p className="empty-desc">No .zip checkpoints found in project checkpoints folder.</p>
      )}
    </div>
  );
}
