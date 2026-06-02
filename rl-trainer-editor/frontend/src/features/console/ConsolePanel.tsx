import { useEffect, useRef, useState } from "react";
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
  const clearLogs = useTrainerStore((s) => s.clearLogs);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

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
          <button type="button" className="header-btn" disabled={logs.length === 0} onClick={() => void copyLogs()}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button type="button" className="header-btn" onClick={clearLogs}>
            Clear
          </button>
        </div>
      </div>
      <div className="console-body">
        {logs.length === 0 && (
          <div className="console-line muted">
            Validation and export events appear here.
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
