import { useEffect, useRef, type ReactNode } from "react";
import { useMonitorStore } from "../../stores/monitorStore";
import type { LogEntry } from "../../types";
import { formatLogTimestamp } from "../../utils/logUtils";
import { parseAnsi } from "../../utils/parseAnsi";

const URL_RE = /https?:\/\/[^\s)]+/g;

function renderMessage(message: string) {
  if (!/https?:\/\//.test(message)) return parseAnsi(message);
  URL_RE.lastIndex = 0;
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of message.matchAll(URL_RE)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(parseAnsi(message.slice(last, index)));
    const href = match[0];
    parts.push(
      <a key={`${index}-${href}`} href={href} target="_blank" rel="noopener noreferrer">
        {href}
      </a>
    );
    last = index + href.length;
  }
  if (last < message.length) parts.push(parseAnsi(message.slice(last)));
  return parts.length === 1 ? parts[0] : parts;
}

function LogLine({ entry }: { entry: LogEntry }) {
  return (
    <div className={`console-line level-${entry.level}`} role="listitem">
      <span className="console-ts" title={entry.timestamp}>
        {formatLogTimestamp(entry.timestamp)}
      </span>
      {entry.component ? (
        <span className="console-component" title="Source">
          {entry.component}
        </span>
      ) : null}
      <span className={`console-level level-${entry.level}`}>{entry.level}</span>
      <span className="console-message">{renderMessage(entry.message)}</span>
    </div>
  );
}

export function ConsolePanel() {
  const logs = useMonitorStore((s) => s.logs);
  const clearLogs = useMonitorStore((s) => s.clearLogs);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="console-panel">
      <div className="console-toolbar">
        <span className="console-toolbar-title">Training log</span>
        <span className="console-toolbar-meta">{logs.length > 0 ? `${logs.length} lines` : ""}</span>
        <button type="button" className="btn small" onClick={clearLogs}>
          Clear
        </button>
      </div>
      <div className="console-body" role="log" aria-live="polite" aria-relevant="additions">
        {logs.length === 0 ? (
          <div className="console-line level-muted">
            <span className="console-message muted">Waiting for training output…</span>
          </div>
        ) : (
          logs.map((entry) => <LogLine key={entry.id} entry={entry} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
