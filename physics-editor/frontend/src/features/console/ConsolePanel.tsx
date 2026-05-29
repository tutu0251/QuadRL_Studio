import { useEffect, useRef } from "react";
import { useEditorStore } from "../../stores/editorStore";

function parseLevel(line: string): "info" | "warn" | "error" | "default" {
  if (line.includes("[error]")) return "error";
  if (line.includes("⚠") || line.includes("warning") || line.includes("failed")) return "warn";
  if (line.includes("complete") || line.includes("Connected") || line.includes("Valid")) return "info";
  return "default";
}

export function ConsolePanel() {
  const logs = useEditorStore((s) => s.logs);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="console-panel">
      <div className="console-body">
        {logs.length === 0 && <div className="console-line muted">Logs from export, validation, and API tasks appear here.</div>}
        {logs.map((line, i) => (
          <div key={i} className={`console-line ${parseLevel(line)}`}>
            {line}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
