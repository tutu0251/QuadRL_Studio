import { useCallback, useEffect, useRef, useState } from "react";
import { useMonitorStore } from "../../stores/monitorStore";
import { ConsolePanel } from "./ConsolePanel";

const HEIGHT_KEY = "quadrl.trainMonitor.consoleHeight";
const EXPAND_KEY = "quadrl.trainMonitor.consoleExpanded";
const DEFAULT_HEIGHT = 240;
const MIN_HEIGHT = 120;
const MAX_RATIO = 0.7;

function loadHeight(): number {
  try {
    const raw = localStorage.getItem(HEIGHT_KEY);
    if (raw) {
      const n = parseInt(raw, 10);
      if (n >= MIN_HEIGHT) return n;
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_HEIGHT;
}

function loadExpanded(): boolean {
  try {
    return localStorage.getItem(EXPAND_KEY) === "1";
  } catch {
    return false;
  }
}

/** Strip ANSI color escapes for the single-line preview. */
function plainText(message: string): string {
  // eslint-disable-next-line no-control-regex
  return message.replace(/\[[0-9;]*m/g, "");
}

/**
 * Console as a top-bar dock: a one-line strip (latest log + chevron) sitting to
 * the right of the page nav. Clicking it drops down a resizable console panel
 * below the top bar; clicking again collapses back to the single line.
 */
export function ConsoleDock() {
  const logs = useMonitorStore((s) => s.logs);
  const [expanded, setExpanded] = useState(loadExpanded);
  const [height, setHeight] = useState(loadHeight);

  const dragging = useRef(false);
  const startY = useRef(0);
  const startHeight = useRef(height);

  const latest = logs.length > 0 ? logs[logs.length - 1] : null;

  const clamp = useCallback((value: number) => {
    const max = Math.max(MIN_HEIGHT, Math.floor(window.innerHeight * MAX_RATIO));
    return Math.min(max, Math.max(MIN_HEIGHT, value));
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = e.clientY - startY.current; // drag down → taller
      setHeight(clamp(startHeight.current + delta));
    };
    const onUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.classList.remove("console-split-dragging");
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [clamp]);

  useEffect(() => {
    try {
      localStorage.setItem(HEIGHT_KEY, String(height));
    } catch {
      /* ignore */
    }
  }, [height]);

  useEffect(() => {
    try {
      localStorage.setItem(EXPAND_KEY, expanded ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [expanded]);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragging.current = true;
    startY.current = e.clientY;
    startHeight.current = height;
    document.body.classList.add("console-split-dragging");
  };

  return (
    <div className={`console-dock ${expanded ? "expanded" : ""}`}>
      <button
        type="button"
        className="console-strip"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        title={expanded ? "Collapse log console" : "Expand log console"}
      >
        <span className={`console-strip-chevron ${expanded ? "open" : ""}`} aria-hidden>
          ▾
        </span>
        <span className="console-strip-label">Console</span>
        {latest ? (
          <span className={`console-strip-latest level-${latest.level}`}>
            <span className={`console-strip-level level-${latest.level}`}>{latest.level}</span>
            {plainText(latest.message)}
          </span>
        ) : (
          <span className="console-strip-latest muted">Waiting for output…</span>
        )}
        <span className="console-strip-count">{logs.length}</span>
      </button>

      {expanded && (
        <div className="console-overlay" style={{ height }}>
          <ConsolePanel />
          <div
            className="console-overlay-resize"
            role="separator"
            aria-orientation="horizontal"
            aria-valuenow={height}
            tabIndex={0}
            onMouseDown={startResize}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") setHeight((h) => clamp(h + 16));
              if (e.key === "ArrowUp") setHeight((h) => clamp(h - 16));
            }}
          />
        </div>
      )}
    </div>
  );
}
