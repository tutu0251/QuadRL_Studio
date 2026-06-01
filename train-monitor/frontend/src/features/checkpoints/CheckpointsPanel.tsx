import type { CheckpointInfo } from "../../types";

type Props = {
  checkpoints: CheckpointInfo[];
  selected: string | null;
  onSelect: (path: string) => void;
};

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function CheckpointsPanel({ checkpoints, selected, onSelect }: Props) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Checkpoints</h2>
        <span className="panel-count">{checkpoints.length}</span>
      </header>
      {checkpoints.length === 0 ? (
        <p className="panel-hint">No .zip checkpoints yet.</p>
      ) : (
        <ul className="item-list">
          {checkpoints.map((ckpt) => (
            <li key={ckpt.path}>
              <button
                type="button"
                className={`list-btn ${selected === ckpt.path ? "selected" : ""}`}
                onClick={() => onSelect(ckpt.path)}
              >
                <span className="list-title">{ckpt.filename}</span>
                <span className="list-meta">
                  {formatBytes(ckpt.size_bytes)} · {new Date(ckpt.modified_at).toLocaleString()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
