import { useEffect, useRef } from "react";
import { useTrainerStore } from "../../stores/trainerStore";

function parseLevel(line: string): "info" | "warn" | "error" | "default" | "muted" {
  if (line.includes("[error]") || line.includes("failed")) return "error";
  if (line.includes("⚠") || line.includes("warning")) return "warn";
  if (line.includes("complete") || line.includes("Connected") || line.includes("OK"))
    return "info";
  if (line.startsWith("  ·")) return "muted";
  return "default";
}

const URL_RE = /https?:\/\/[^\s)]+/g;

function renderLine(line: string) {
  const parts: (string | JSX.Element)[] = [];
  let last = 0;
  for (const match of line.matchAll(URL_RE)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(line.slice(last, index));
    const href = match[0];
    parts.push(
      <a key={`${index}-${href}`} href={href} target="_blank" rel="noopener noreferrer">
        {href}
      </a>
    );
    last = index + href.length;
  }
  if (last < line.length) parts.push(line.slice(last));
  return parts.length ? parts : line;
}

export function ConsolePanel() {
  const logs = useTrainerStore((s) => s.logs);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="console-panel">
      <div className="console-body">
        {logs.length === 0 && (
          <div className="console-line muted">
            Presets, validation, and export events appear here.
          </div>
        )}
        {logs.map((line, i) => (
          <div key={i} className={`console-line ${parseLevel(line)}`}>
            {renderLine(line)}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
