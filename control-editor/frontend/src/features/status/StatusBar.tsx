import { PROFILE_LABELS } from "@control-model";
import { useEditorStore } from "../../stores/editorStore";

export function StatusBar({ connected }: { connected: boolean }) {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);

  const jointName = selection?.kind === "joint" ? selection.name : null;

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
          <span className="status-item">{PROFILE_LABELS[model.trainingProfile]}</span>
        </>
      )}
      {jointName && (
        <>
          <span className="status-sep">|</span>
          <span className="status-item">{jointName}</span>
        </>
      )}
      <span className="status-spacer" />
      <span className="status-item muted">ros2_control export</span>
    </footer>
  );
}
