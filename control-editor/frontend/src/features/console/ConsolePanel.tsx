import { useEffect, useRef } from "react";
import { useEditorStore } from "../../stores/editorStore";

function parseLevel(line: string): "info" | "warn" | "error" | "default" {
  if (line.includes("[error]") || line.includes("failed") || line.includes("Failed")) return "error";
  if (line.includes("⚠") || line.includes("warning") || line.includes("not implemented")) return "warn";
  if (line.includes("complete") || line.includes("Connected") || line.includes("Valid") || line.includes("passed"))
    return "info";
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
        {logs.length === 0 && (
          <div className="console-line muted">Validation, export, and profile changes log here.</div>
        )}
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
