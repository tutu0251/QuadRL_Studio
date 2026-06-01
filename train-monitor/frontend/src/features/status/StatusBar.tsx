type Props = {
  connected: boolean;
  project: string | null;
};

export function StatusBar({ connected, project }: Props) {
  return (
    <footer className="status-bar">
      <span className={connected ? "status-ok" : "status-err"}>
        {connected ? "Connected" : "Disconnected"}
      </span>
      <span>{project ? `Project: ${project}` : "No project loaded"}</span>
      <span>Backend :8006 · UI :5179</span>
    </footer>
  );
}
