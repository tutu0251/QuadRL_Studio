import { useEditorStore } from "../../stores/editorStore";

export function StatusBar({ connected }: { connected: boolean }) {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);

  const selLabel =
    selection?.kind === "sensor"
      ? model?.sensors.find((s) => s.id === selection.id)?.name
      : selection?.kind === "link"
        ? selection.name
        : null;

  return (
    <footer className="status-bar">
      <span
        className={`status-dot ${connected ? "online" : "offline"}`}
        title={connected ? "API connected" : "API offline"}
      />
      <span className="status-item">{connected ? "Connected" : "Offline"}</span>
      <span className="status-sep">|</span>
      <span className="status-item">{project ? `Project: ${project}` : "No project"}</span>
      {model && (
        <>
          <span className="status-sep">|</span>
          <span className="status-item">{model.sensors.length} sensors</span>
        </>
      )}
      {selLabel && (
        <>
          <span className="status-sep">|</span>
          <span className="status-item">{selLabel}</span>
        </>
      )}
      <span className="status-spacer" />
      <span className="status-item muted">RL package export</span>
    </footer>
  );
}
