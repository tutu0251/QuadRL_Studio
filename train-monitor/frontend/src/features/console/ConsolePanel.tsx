import { useMonitorStore } from "../../stores/monitorStore";

export function ConsolePanel() {
  const logs = useMonitorStore((s) => s.logs);
  const clearLogs = useMonitorStore((s) => s.clearLogs);

  return (
    <div className="console-panel">
      <div className="console-toolbar">
        <span>Training log</span>
        <button type="button" className="btn small" onClick={clearLogs}>
          Clear
        </button>
      </div>
      <pre className="console-output">
        {logs.length === 0 ? "Waiting for training output…" : logs.join("\n")}
      </pre>
    </div>
  );
}
