import { useEditorStore } from "../../stores/editorStore";

export function StatusBar({ connected }: { connected: boolean }) {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const wholeCom = useEditorStore((s) => s.wholeCom);

  const selLink =
    selection?.kind === "link" ? model?.links.find((l) => l.id === selection.id) : undefined;

  return (
    <footer className="status-bar">
      <span className={`status-dot ${connected ? "online" : "offline"}`} title={connected ? "API connected" : "API offline"} />
      <span className="status-item">{connected ? "Connected" : "Offline"}</span>
      <span className="status-sep">|</span>
      <span className="status-item">{project ? `Project: ${project}` : "No project"}</span>
      {selLink && (
        <>
          <span className="status-sep">|</span>
          <span className="status-item">
            {selLink.name} · m={selLink.inertial.mass.toFixed(3)} kg
            {selLink.isFoot ? " · foot" : ""}
          </span>
        </>
      )}
      {wholeCom && (
        <>
          <span className="status-sep">|</span>
          <span className="status-item status-com">
            Robot COM ({wholeCom.x.toFixed(3)}, {wholeCom.y.toFixed(3)}, {wholeCom.z.toFixed(3)}) m
          </span>
        </>
      )}
      <span className="status-spacer" />
      <span className="status-item muted">SI · phy_ export</span>
    </footer>
  );
}
