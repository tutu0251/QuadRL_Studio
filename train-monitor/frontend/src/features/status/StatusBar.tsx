type Props = {
  connected: boolean;
  project: string | null;
  trainingActive?: boolean;
};

export function StatusBar({ connected, project, trainingActive }: Props) {
  return (
    <footer className="status-bar">
      <span className={connected ? "status-ok" : "status-err"}>
        {connected ? "API connected" : "API disconnected"}
      </span>
      <span>{project ? `Project · ${project}` : "No project"}</span>
      {trainingActive && <span className="status-training">Training in progress</span>}
      <span className="status-ports">:8006 · :5179</span>
    </footer>
  );
}
