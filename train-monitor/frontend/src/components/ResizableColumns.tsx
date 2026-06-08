import { Children, Fragment, useEffect, useRef, useState, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  /** localStorage key to persist the column widths */
  storageKey?: string;
  /** minimum width of any column as a fraction of the total (0–1) */
  minFraction?: number;
};

function loadWeights(key: string | undefined, n: number): number[] {
  if (key) {
    try {
      const raw = localStorage.getItem(key);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr) && arr.length === n && arr.every((x) => typeof x === "number" && x > 0)) {
          return arr;
        }
      }
    } catch {
      /* ignore */
    }
  }
  return Array(n).fill(1);
}

/**
 * Lays its children out as horizontal columns separated by draggable splitters.
 * Columns are sized by flex-grow weights; dragging a splitter transfers weight
 * between the two adjacent columns. Widths persist to localStorage.
 */
export function ResizableColumns({ children, storageKey, minFraction = 0.12 }: Props) {
  const items = Children.toArray(children);
  const n = items.length;
  const containerRef = useRef<HTMLDivElement>(null);
  const [weights, setWeights] = useState<number[]>(() => loadWeights(storageKey, n));
  const drag = useRef<{ index: number; startX: number; startW: number[] } | null>(null);

  // Reset if the number of columns changes.
  useEffect(() => {
    setWeights((w) => (w.length === n ? w : loadWeights(storageKey, n)));
  }, [n, storageKey]);

  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(weights));
    } catch {
      /* ignore */
    }
  }, [weights, storageKey]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const d = drag.current;
      const el = containerRef.current;
      if (!d || !el) return;
      const total = d.startW.reduce((a, b) => a + b, 0);
      const width = el.clientWidth || 1;
      const dWeight = ((e.clientX - d.startX) / width) * total;
      const min = total * minFraction;
      let a = d.startW[d.index] + dWeight;
      let b = d.startW[d.index + 1] - dWeight;
      if (a < min) {
        b -= min - a;
        a = min;
      }
      if (b < min) {
        a -= min - b;
        b = min;
      }
      const next = [...d.startW];
      next[d.index] = a;
      next[d.index + 1] = b;
      setWeights(next);
    };
    const onUp = () => {
      if (!drag.current) return;
      drag.current = null;
      document.body.classList.remove("col-resizing");
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [minFraction]);

  const startDrag = (index: number) => (e: React.MouseEvent) => {
    e.preventDefault();
    drag.current = { index, startX: e.clientX, startW: [...weights] };
    document.body.classList.add("col-resizing");
  };

  return (
    <div className="resizable-cols" ref={containerRef}>
      {items.map((child, i) => (
        <Fragment key={i}>
          <div className="resizable-col" style={{ flexGrow: weights[i] ?? 1, flexBasis: 0 }}>
            {child}
          </div>
          {i < n - 1 && (
            <div
              className="col-splitter"
              role="separator"
              aria-orientation="vertical"
              onMouseDown={startDrag(i)}
            />
          )}
        </Fragment>
      ))}
    </div>
  );
}
