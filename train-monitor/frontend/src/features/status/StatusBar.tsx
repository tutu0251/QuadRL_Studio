import type { TrainStatus } from "../../types";

type Props = {
  connected: boolean;
  project: string | null;
  trainingActive?: boolean;
  trainStatus?: TrainStatus | null;
};

function formatTimesteps(progressMessage?: string | null): string | null {
  if (!progressMessage) return null;
  // Backend sends "<done> / <total> timesteps".
  const match = progressMessage.match(/^([\d,]+)\s*\/\s*([\d,]+)/);
  if (!match) return null;
  const done = Number(match[1].replace(/,/g, ""));
  const total = Number(match[2].replace(/,/g, ""));
  if (!Number.isFinite(done) || !Number.isFinite(total) || total <= 0) return null;
  const ratio = ((done / total) * 100).toFixed(1);
  // [current/stage timesteps] : overall progress ratio
  return `[${done.toLocaleString()}/${total.toLocaleString()}] : ${ratio}%`;
}

export function StatusBar({ connected, project, trainingActive, trainStatus }: Props) {
  const timesteps = formatTimesteps(trainStatus?.progress_message);
  const episodes = trainStatus?.episode_count;
  const termCounts = trainStatus?.termination_counts ?? {};
  const termEntries = Object.entries(termCounts).sort((a, b) => b[1] - a[1]);

  return (
    <footer className="status-bar">
      <span className={connected ? "status-ok" : "status-err"}>
        {connected ? "API connected" : "API disconnected"}
      </span>
      <span>{project ? `Project · ${project}` : "No project"}</span>
      {trainingActive && <span className="status-training">Training in progress</span>}
      {timesteps != null && (
        <span className="status-train-stat" title="[current/stage timesteps] : overall progress">
          {timesteps}
        </span>
      )}
      {episodes != null && (
        <span className="status-train-stat" title="Episodes completed">
          episodes {episodes.toLocaleString()}
        </span>
      )}
      {termEntries.length > 0 && (
        <span className="status-term-counts" title="Termination reasons">
          {termEntries.map(([reason, count]) => (
            <span key={reason} className="status-term-count">
              {reason} : {count}
            </span>
          ))}
        </span>
      )}
      <span className="status-ports">:8006 · :5179</span>
    </footer>
  );
}
