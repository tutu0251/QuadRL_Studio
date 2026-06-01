import { formatBytes, formatTimestamp } from "../../utils/format";
import type { CheckpointInfo } from "../../types";

type Props = {
  checkpoints: CheckpointInfo[];
  selected: string | null;
  onSelect: (path: string) => void;
};

export function CheckpointsPanel({ checkpoints, selected, onSelect }: Props) {
  return (
    <section className="panel checkpoints-panel">
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
                <span className="list-meta">{formatBytes(ckpt.size_bytes)}</span>
                <time className="list-timestamp" dateTime={ckpt.modified_at}>
                  {formatTimestamp(ckpt.modified_at)}
                </time>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
