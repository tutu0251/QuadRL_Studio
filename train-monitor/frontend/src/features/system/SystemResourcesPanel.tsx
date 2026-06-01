import { useEffect, useId, useRef, useState, type CSSProperties } from "react";
import { api } from "../../api/client";
import type { SystemStatsSample } from "../../types";

const HISTORY_LEN = 48;
const POLL_MS = 1000;

function sparklinePath(values: number[], w: number, h: number, pad: number): string {
  if (values.length === 0) return "";
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = pad + (i / Math.max(1, values.length - 1)) * (w - pad * 2);
    const y = pad + (1 - (v - min) / range) * (h - pad * 2);
    return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  });
  return pts.join(" ");
}

function ResourceGauge({
  label,
  percent,
  sub,
  accent,
  history,
  gridId,
}: {
  label: string;
  percent: number;
  sub: string;
  accent: string;
  history: number[];
  gridId: string;
}) {
  const w = 100;
  const h = 40;
  const pad = 2;
  const path = sparklinePath(history, w, h, pad);
  const pct = Math.min(100, Math.max(0, percent));

  return (
    <div className="resource-gauge" style={{ "--gauge-accent": accent } as CSSProperties}>
      <div className="resource-gauge-head">
        <span className="resource-gauge-label">{label}</span>
        <span className="resource-gauge-pct">{pct.toFixed(1)}%</span>
      </div>
      <div className="resource-gauge-bar">
        <div className="resource-gauge-fill" style={{ width: `${pct}%` }} />
      </div>
      <svg className="resource-sparkline" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden>
        <defs>
          <pattern id={`rg-${gridId}-${label}`} width="8" height="8" patternUnits="userSpaceOnUse">
            <path d="M 8 0 L 0 0 0 8" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width={w} height={h} fill={`url(#rg-${gridId}-${label})`} />
        {path && <path d={path} fill="none" stroke={accent} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />}
      </svg>
      <span className="resource-gauge-sub">{sub}</span>
    </div>
  );
}

export function SystemResourcesPanel() {
  const gridId = useId().replace(/:/g, "");
  const [sample, setSample] = useState<SystemStatsSample | null>(null);
  const [cpuHist, setCpuHist] = useState<number[]>(() => Array(HISTORY_LEN).fill(0));
  const [ramHist, setRamHist] = useState<number[]>(() => Array(HISTORY_LEN).fill(0));
  const [gpuHist, setGpuHist] = useState<number[]>(() => Array(HISTORY_LEN).fill(0));
  const [live, setLive] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await api.systemStats();
        if (!mounted.current) return;
        setSample(data);
        setCpuHist((p) => [...p.slice(1), data.cpuPercent]);
        setRamHist((p) => [...p.slice(1), data.ramUsedPercent]);
        const gpuPct = data.gpuUtilPercent ?? (data.gpuMemoryPercent ?? 0);
        setGpuHist((p) => [...p.slice(1), gpuPct]);
        setLive(true);
      } catch {
        if (mounted.current) setLive(false);
      }
    };
    void poll();
    const id = window.setInterval(() => void poll(), POLL_MS);
    return () => window.clearInterval(id);
  }, []);

  const gpuPct = sample?.gpuUtilPercent ?? sample?.gpuMemoryPercent ?? 0;
  const gpuSub = sample?.gpuAvailable
    ? `${sample.gpuName} · ${sample.gpuMemoryUsedMb?.toFixed(0) ?? "?"} / ${sample.gpuMemoryTotalMb?.toFixed(0) ?? "?"} MB VRAM`
    : "No GPU detected";

  return (
    <section className="panel system-panel" aria-label="Host resources">
      <header className="panel-header">
        <h2>
          Host
          <span className={`live-dot ${live ? "on" : ""}`} title={live ? "Live" : "Offline"} />
        </h2>
        <span className="panel-meta mono">{sample?.hostname ?? "—"}</span>
      </header>

      <div className="resource-gauges">
        <ResourceGauge
          label="CPU"
          percent={sample?.cpuPercent ?? 0}
          sub={`${sample?.cpuCountLogical ?? "—"} logical cores`}
          accent="#5c9fd4"
          history={cpuHist}
          gridId={gridId}
        />
        <ResourceGauge
          label="RAM"
          percent={sample?.ramUsedPercent ?? 0}
          sub={
            sample
              ? `${sample.ramUsedMb.toLocaleString()} / ${sample.ramTotalMb.toLocaleString()} MB`
              : "—"
          }
          accent="#9b7ed9"
          history={ramHist}
          gridId={gridId}
        />
        <ResourceGauge
          label="GPU"
          percent={sample?.gpuAvailable ? gpuPct : 0}
          sub={gpuSub}
          accent="#e8a54a"
          history={gpuHist}
          gridId={gridId}
        />
      </div>
    </section>
  );
}
