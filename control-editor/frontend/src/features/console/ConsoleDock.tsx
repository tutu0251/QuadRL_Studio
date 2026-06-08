import { useCallback, useEffect, useRef, useState } from "react";
import { useEditorStore } from "../../stores/editorStore";
import { ConsolePanel } from "./ConsolePanel";

const HEIGHT_KEY = "quadrl.controlEditor.consoleHeight";
const EXPAND_KEY = "quadrl.controlEditor.consoleExpanded";
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

/**
 * Console as a top-bar dock: a one-line strip (latest log + chevron) to the
 * right of the action toolbar. Clicking drops down a resizable console panel;
 * clicking again collapses back to a single line.
 */
export function ConsoleDock() {
  const logs = useEditorStore((s) => s.logs);
  const consoleFocus = useEditorStore((s) => s.consoleFocus);
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

  // Auto-expand when something requests console focus (validation/export errors).
  useEffect(() => {
    if (consoleFocus > 0) setExpanded(true);
  }, [consoleFocus]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      setHeight(clamp(startHeight.current + (e.clientY - startY.current)));
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
        title={expanded ? "Collapse console" : "Expand console"}
      >
        <span className={`console-strip-chevron ${expanded ? "open" : ""}`} aria-hidden>
          ▾
        </span>
        <span className="console-strip-label">Console</span>
        <span className="console-strip-latest">
          {latest ?? "Validation, export, and profile changes log here."}
        </span>
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
