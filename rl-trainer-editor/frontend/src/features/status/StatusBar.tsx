import { useTrainerStore } from "../../stores/trainerStore";

type Props = { connected: boolean };

export function StatusBar({ connected }: Props) {
  const project = useTrainerStore((s) => s.project);
  return (
    <footer className="status-bar">
      <span className={`status-dot ${connected ? "online" : "offline"}`} />
      <span>{connected ? "API connected" : "API offline"}</span>
      <span className="status-spacer" />
      {project && <span className="mono">project: {project}</span>}
      <span className="status-meta">:8005 · :5178</span>
    </footer>
  );
}
