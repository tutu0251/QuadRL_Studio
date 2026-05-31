import { useEffect, useId, useRef, useState } from "react";
import type { RamMemorySample } from "@rl-trainer-model";
import { api } from "../../api/client";

const HISTORY_LEN = 60;
const POLL_MS = 500;

function formatExactMb(mb: number): string {
  return `${mb.toLocaleString()} MB`;
}

function formatExactGb(gb: number): string {
  return `${gb.toFixed(3)} GB`;
}

export function MemoryUsageGraph({
  initialTotalMb,
  initialUsedMb,
}: {
  initialTotalMb: number;
  initialUsedMb: number;
}) {
  const gridId = useId().replace(/:/g, "");
  const [sample, setSample] = useState<RamMemorySample | null>(() =>
    initialTotalMb > 0
      ? {
          ramTotalGb: initialTotalMb / 1024,
          ramUsedGb: initialUsedMb / 1024,
          ramAvailableGb: Math.max(0, initialTotalMb - initialUsedMb) / 1024,
          ramTotalMb: initialTotalMb,
          ramUsedMb: initialUsedMb,
          ramAvailableMb: Math.max(0, initialTotalMb - initialUsedMb),
          sampledAt: "",
        }
      : null
  );
  const [history, setHistory] = useState<number[]>(() =>
    Array.from({ length: HISTORY_LEN }, () => initialUsedMb)
  );
  const [live, setLive] = useState(false);
  const [pollError, setPollError] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await api.machineMemory();
        if (!mountedRef.current) return;
        setSample(data);
        setHistory((prev) => [...prev.slice(1), data.ramUsedMb]);
        setLive(true);
        setPollError(false);
      } catch {
        if (mountedRef.current) {
          setLive(false);
          setPollError(true);
        }
      }
    };

    void poll();
    const id = window.setInterval(() => void poll(), POLL_MS);
    return () => window.clearInterval(id);
  }, []);

  const totalMb = sample?.ramTotalMb ?? initialTotalMb;
  const usedMb = sample?.ramUsedMb ?? initialUsedMb;
  const availableMb = sample?.ramAvailableMb ?? Math.max(0, totalMb - usedMb);
  const usedGb = sample?.ramUsedGb ?? initialUsedMb / 1024;

  const maxY = Math.max(totalMb, 1);
  const w = 100;
  const h = 56;
  const pad = 2;

  const points = history.map((used, i) => {
    const x = pad + (i / Math.max(1, HISTORY_LEN - 1)) * (w - pad * 2);
    const y = pad + (1 - Math.min(used, maxY) / maxY) * (h - pad * 2);
    return { x, y };
  });

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1]?.x.toFixed(2) ?? pad} ${h - pad} L ${points[0]?.x.toFixed(2) ?? pad} ${h - pad} Z`;

  const headroomPct = totalMb > 0 ? (availableMb / totalMb) * 100 : 0;

  return (
    <section className="memory-graph-section memory-graph-dark" aria-label="Memory usage">
      <div className="memory-graph-header">
        <div>
          <h4 className="memory-graph-title">
            Memory
            <span className={`memory-live-dot ${live ? "on" : ""}`} title={live ? "Live" : "Offline"} />
          </h4>
          <span className="memory-graph-subtitle">Realtime host RAM · {POLL_MS}ms refresh</span>
        </div>
        <span className="memory-graph-total">{formatExactMb(totalMb)}</span>
      </div>

      <div className="memory-graph-wrap">
        <span className="memory-graph-y-label">{formatExactMb(usedMb)}</span>
        <svg
          className="memory-graph-svg"
          viewBox={`0 0 ${w} ${h}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={`Memory in use ${formatExactMb(usedMb)} of ${formatExactMb(totalMb)}`}
        >
          <defs>
            <pattern id={`memGrid-${gridId}`} width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="0.5" />
            </pattern>
            <linearGradient id={`memFill-${gridId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(155, 126, 217, 0.45)" />
              <stop offset="100%" stopColor="rgba(106, 79, 184, 0.08)" />
            </linearGradient>
          </defs>
          <rect x="0" y="0" width={w} height={h} fill={`url(#memGrid-${gridId})`} />
          <rect x="0" y="0" width={w} height={h} fill="#161920" />
          <rect x="0" y="0" width={w} height={h} fill={`url(#memGrid-${gridId})`} />
          <path d={areaPath} fill={`url(#memFill-${gridId})`} />
          <path d={linePath} className="memory-graph-line" fill="none" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="memory-graph-x-axis">
          <span>60 seconds</span>
          <span>now</span>
        </div>
      </div>

      <div className="memory-graph-foot">
        <div className="memory-exact-row">
          <span className="memory-graph-chip">
            In use · <strong>{formatExactMb(usedMb)}</strong>
            <span className="memory-graph-subvalue"> ({formatExactGb(usedGb)})</span>
          </span>
        </div>
        <div className="memory-exact-row">
          <span className="memory-graph-chip muted">
            Available · {formatExactMb(availableMb)}
          </span>
          <span className="memory-graph-chip muted">
            Headroom · {headroomPct.toFixed(1)}%
          </span>
        </div>
        {pollError && (
          <span className="memory-graph-chip warn">Could not reach host memory API</span>
        )}
      </div>
    </section>
  );
}
