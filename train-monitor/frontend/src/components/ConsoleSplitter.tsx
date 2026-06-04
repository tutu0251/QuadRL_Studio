import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

const STORAGE_KEY = "quadrl.trainMonitor.consoleHeight";
const DEFAULT_HEIGHT = 180;
const MIN_HEIGHT = 96;
const MAX_RATIO = 0.65;

function loadHeight(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const n = parseInt(raw, 10);
      if (n >= MIN_HEIGHT) return n;
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_HEIGHT;
}

type Props = {
  children: ReactNode;
};

export function ConsoleSplitter({ children }: Props) {
  const [height, setHeight] = useState(loadHeight);
  const dragging = useRef(false);
  const startY = useRef(0);
  const startHeight = useRef(height);

  const clamp = useCallback((value: number) => {
    const max = Math.max(MIN_HEIGHT, Math.floor(window.innerHeight * MAX_RATIO));
    return Math.min(max, Math.max(MIN_HEIGHT, value));
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = startY.current - e.clientY;
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
      localStorage.setItem(STORAGE_KEY, String(height));
    } catch {
      /* ignore */
    }
  }, [height]);

  const onMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    startY.current = e.clientY;
    startHeight.current = height;
    document.body.classList.add("console-split-dragging");
  };

  return (
    <>
      <div
        className="console-splitter"
        role="separator"
        aria-orientation="horizontal"
        aria-valuenow={height}
        tabIndex={0}
        onMouseDown={onMouseDown}
        onKeyDown={(e) => {
          if (e.key === "ArrowUp") setHeight((h) => clamp(h + 16));
          if (e.key === "ArrowDown") setHeight((h) => clamp(h - 16));
        }}
      />
      <div className="bottom-dock" style={{ height }}>
        {children}
      </div>
    </>
  );
}
