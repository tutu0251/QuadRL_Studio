import { useEffect, useRef } from "react";
import { usePlannerStore } from "../../stores/plannerStore";

function parseLevel(line: string): "info" | "warn" | "error" | "default" | "muted" {
  if (line.includes("[error]") || line.includes("failed")) return "error";
  if (line.includes("⚠") || line.includes("warning")) return "warn";
  if (line.includes("complete") || line.includes("Connected") || line.includes("OK"))
    return "info";
  if (line.startsWith("  ·")) return "muted";
  return "default";
}

export function ConsolePanel() {
  const logs = usePlannerStore((s) => s.logs);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="console-panel">
      <div className="console-body">
        {logs.length === 0 && (
          <div className="console-line muted">
            Recommendations, validation, and export events appear here.
          </div>
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
