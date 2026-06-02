import { useState } from "react";
import { useMonitorStore } from "../../stores/monitorStore";
import { parseAnsiToSegments } from "./ansi";

function levelLabel(level: string) {
  return level.toUpperCase();
}

function AnsiMessage({ text }: { text: string }) {
  const segs = parseAnsiToSegments(text);
  return (
    <>
      {segs.map((s, i) => (
        <span key={i} className={s.className}>
          {s.text}
        </span>
      ))}
    </>
  );
}

export function ConsolePanel() {
  const logs = useMonitorStore((s) => s.logs);
  const clearLogs = useMonitorStore((s) => s.clearLogs);
  const [copied, setCopied] = useState(false);

  const copyLogs = async () => {
    const text = logs.map((l) => l.rawLine).join("\n");
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
      <div className="console-output console-lines mono" role="log" aria-live="polite">
        {logs.length === 0 ? (
          <div className="console-empty">Waiting for training output…</div>
        ) : (
          logs.map((l, idx) => (
            <div key={`${l.ts}-${idx}`} className={`console-line console-${l.level}`}>
              <span className="console-ts">[{l.ts}]</span>
              <span className={`console-pill console-level console-level-${l.level}`}>{levelLabel(l.level)}</span>
              {l.component ? (
                <span className={`console-pill console-comp console-comp-${l.component}`}>{l.component}</span>
              ) : null}
              <span className="console-msg">
                <AnsiMessage text={l.message} />
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
