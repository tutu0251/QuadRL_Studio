import { useState } from "react";
import { useMonitorStore } from "../../stores/monitorStore";

export function ConsolePanel() {
  const logs = useMonitorStore((s) => s.logs);
  const clearLogs = useMonitorStore((s) => s.clearLogs);
  const [copied, setCopied] = useState(false);

  const copyLogs = async () => {
    const text = logs.join("\n");
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="console-panel">
      <div className="console-toolbar">
        <span className="console-toolbar-title">Output</span>
        <div className="console-toolbar-actions">
          <button type="button" className="btn small" disabled={logs.length === 0} onClick={() => void copyLogs()}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button type="button" className="btn small" onClick={clearLogs}>
            Clear
          </button>
        </div>
      </div>
      <pre className="console-output">
        {logs.length === 0 ? "Waiting for training output…" : logs.join("\n")}
      </pre>
    </div>
  );
}
