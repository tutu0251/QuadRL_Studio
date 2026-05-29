import { useEditorStore } from "../../stores/editorStore";

export function ConsolePanel() {
  const logs = useEditorStore((s) => s.logs);

  return (
    <div className="console-panel">
      <div className="panel-header">Console</div>
      <div className="console-body">
        {logs.length === 0 ? (
          <p className="panel-empty">No messages</p>
        ) : (
          logs.slice(-50).map((l, i) => (
            <div key={i} className="console-line">{l}</div>
          ))
        )}
      </div>
    </div>
  );
}
