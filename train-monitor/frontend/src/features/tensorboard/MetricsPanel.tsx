import { useId, useMemo, type CSSProperties } from "react";
import { getApiBaseUrl, tbOpenUrl } from "../../api/client";
import { ActionButton } from "../../components/ActionButton";
import type { ScalarSeries, TensorBoardStatus } from "../../types";

type Props = {
  project: string | null;
  scalars: ScalarSeries[];
  tbStatus: TensorBoardStatus | null;
  trainingActive: boolean;
  onOpenTb: () => void;
  onStopTb: () => void;
  busy: boolean;
  tbStartCommand?: string | null;
  tbStopCommand?: string | null;
  tbStartLoading?: boolean;
  tbStopLoading?: boolean;
};

const TB_COLORS = ["#e8a54a", "#5c9fd4", "#66bb6a", "#ce93d8", "#ef5350", "#80cbc4"];

/** Show core RL metrics first (matches training/scripts/tb_callbacks.py). */
const FUNDAMENTAL_PREFIXES = ["rollout/", "eval/", "train/", "time/"];

function scalarSortKey(tag: string): [number, string] {
  const idx = FUNDAMENTAL_PREFIXES.findIndex((p) => tag.startsWith(p));
  return [idx === -1 ? FUNDAMENTAL_PREFIXES.length : idx, tag];
}

function smoothValues(values: number[], weight = 0.6): number[] {
  if (values.length === 0) return [];
  let last = values[0];
  return values.map((v) => {
    last = last * weight + v * (1 - weight);
    return last;
  });
}

function TensorBoardChart({ series, colorIndex }: { series: ScalarSeries; colorIndex: number }) {
  const gridId = useId().replace(/:/g, "");
  const { steps, values } = series;
  const color = TB_COLORS[colorIndex % TB_COLORS.length];
  const smoothed = useMemo(() => smoothValues(values), [values]);

  if (values.length === 0) {
    return <div className="tb-chart empty">No data</div>;
  }

  const plotValues = smoothed;
  const min = Math.min(...plotValues);
  const max = Math.max(...plotValues);
  const range = max - min || 1;
  const w = 400;
  const h = 140;
  const padL = 44;
  const padR = 8;
  const padT = 12;
  const padB = 24;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const points = plotValues
    .map((v, i) => {
      const x = padL + (i / Math.max(1, plotValues.length - 1)) * plotW;
      const y = padT + plotH - ((v - min) / range) * plotH;
      return `${x},${y}`;
    })
    .join(" ");

  const lastVal = values[values.length - 1];
  const lastStep = steps[steps.length - 1];
  const yTicks = [min, min + range * 0.5, max];

  return (
    <article className="tb-chart" style={{ "--chart-color": color } as CSSProperties}>
      <header className="tb-chart-header">
        <h3 className="tb-chart-tag" title={series.tag}>
          {series.tag}
        </h3>
        <span className="tb-chart-value">{lastVal?.toPrecision(4)}</span>
      </header>
      <svg viewBox={`0 0 ${w} ${h}`} className="tb-chart-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
          <pattern id={`grid-${gridId}`} width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect x={padL} y={padT} width={plotW} height={plotH} fill={`url(#grid-${gridId})`} />
        {yTicks.map((tick, i) => {
          const y = padT + plotH - ((tick - min) / range) * plotH;
          return (
            <g key={i}>
              <line x1={padL} y1={y} x2={padL + plotW} y2={y} stroke="rgba(255,255,255,0.08)" />
              <text x={padL - 4} y={y + 3} textAnchor="end" className="tb-axis-label">
                {tick.toPrecision(3)}
              </text>
            </g>
          );
        })}
        <polyline fill="none" stroke={color} strokeWidth="2" points={points} />
        <text x={padL} y={h - 6} className="tb-axis-label">
          step {steps[0]}
        </text>
        <text x={padL + plotW} y={h - 6} textAnchor="end" className="tb-axis-label">
          step {lastStep}
        </text>
      </svg>
    </article>
  );
}

export function MetricsPanel({
  project,
  scalars,
  tbStatus,
  trainingActive,
  onOpenTb,
  onStopTb,
  busy,
  tbStartCommand,
  tbStopCommand,
  tbStartLoading,
  tbStopLoading,
}: Props) {
  const tbLink =
    project && tbStatus?.running
      ? `${getApiBaseUrl()}${tbStatus.open_url ?? tbOpenUrl(project)}`
      : null;

  const sortedScalars = useMemo(
    () => [...scalars].sort((a, b) => {
      const [pa, ta] = scalarSortKey(a.tag);
      const [pb, tb] = scalarSortKey(b.tag);
      return pa !== pb ? pa - pb : ta.localeCompare(tb);
    }),
    [scalars],
  );

  return (
    <section className="panel metrics-panel">
      <header className="panel-header">
        <div>
          <h2>Training metrics</h2>
          <p className="panel-subtitle">
            TensorBoard-style scalars from event files
            {trainingActive && <span className="metrics-live"> · updating live</span>}
          </p>
        </div>
        <div className="btn-row inline metrics-tb-actions">
          {!tbStatus?.running ? (
            <ActionButton
              className="btn small accent"
              disabled={busy || !project}
              command={tbStartCommand}
              commandLoading={tbStartLoading}
              onClick={onOpenTb}
            >
              TensorBoard
            </ActionButton>
          ) : (
            <>
              {tbLink && (
                <a className="btn small link accent" href={tbLink} target="_blank" rel="noreferrer">
                  Open TensorBoard
                </a>
              )}
              <ActionButton
                className="btn small ghost"
                disabled={busy}
                command={tbStopCommand}
                commandLoading={tbStopLoading}
                onClick={onStopTb}
              >
                Stop TB
              </ActionButton>
            </>
          )}
        </div>
      </header>

      {tbStatus?.error && <p className="panel-warn">{tbStatus.error}</p>}

      <div className="tb-chart-grid">
        {scalars.length === 0 ? (
          <p className="panel-hint metrics-empty">
            {trainingActive
              ? "Waiting for metrics — PPO logs one point per rollout (~2k env steps). With the ROS sim this is often 1–2 minutes before the first chart appears."
              : "No scalar metrics yet — start training or select a run with TensorBoard event files."}
          </p>
        ) : (
          sortedScalars.map((s, i) => <TensorBoardChart key={s.tag} series={s} colorIndex={i} />)
        )}
      </div>
    </section>
  );
}
