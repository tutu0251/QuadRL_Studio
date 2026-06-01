import type { ScalarSeries, TensorBoardStatus } from "../../types";
import { getApiBaseUrl } from "../../api/client";

type Props = {
  scalars: ScalarSeries[];
  tbStatus: TensorBoardStatus | null;
  onStartTb: () => void;
  onStopTb: () => void;
  busy: boolean;
};

function MiniChart({ series }: { series: ScalarSeries }) {
  const { steps, values } = series;
  if (values.length === 0) {
    return <div className="mini-chart empty">No data</div>;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 280;
  const h = 72;
  const lastVal = values[values.length - 1];
  const lastStep = steps[steps.length - 1];

  let polyline = "";
  if (values.length === 1) {
    const y = h / 2;
    polyline = `0,${y} ${w},${y}`;
  } else {
    polyline = values
      .map((v, i) => {
        const x = (i / (values.length - 1)) * w;
        const y = h - ((v - min) / range) * (h - 8) - 4;
        return `${x},${y}`;
      })
      .join(" ");
  }

  return (
    <div className="mini-chart">
      <div className="mini-chart-head">
        <span>{series.tag}</span>
        <span className="mini-chart-val">{lastVal?.toFixed(4)}</span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        <polyline fill="none" stroke="currentColor" strokeWidth="1.5" points={polyline} />
      </svg>
      <div className="mini-chart-foot">step {lastStep}</div>
    </div>
  );
}

export function TensorBoardPanel({ scalars, tbStatus, onStartTb, onStopTb, busy }: Props) {
  const embedSrc = tbStatus?.running && tbStatus.embed_url ? `${getApiBaseUrl()}${tbStatus.embed_url}` : null;

  return (
    <section className="panel tb-panel">
      <header className="panel-header">
        <h2>Metrics</h2>
        <div className="btn-row inline">
          {!tbStatus?.running ? (
            <button type="button" className="btn small" disabled={busy} onClick={onStartTb}>
              Open TensorBoard
            </button>
          ) : (
            <>
              {tbStatus.url && (
                <a className="btn small link" href={embedSrc ?? "#"} target="_blank" rel="noreferrer">
                  Open in tab
                </a>
              )}
              <button type="button" className="btn small" disabled={busy} onClick={onStopTb}>
                Stop TB
              </button>
            </>
          )}
        </div>
      </header>

      {tbStatus?.error && <p className="panel-warn">{tbStatus.error}</p>}

      {embedSrc && (
        <iframe className="tb-iframe" title="TensorBoard" src={embedSrc} />
      )}

      <div className="scalar-grid">
        {scalars.length === 0 ? (
          <p className="panel-hint">No scalar metrics yet — start training or select a run with event files.</p>
        ) : (
          scalars.slice(0, 8).map((s) => <MiniChart key={s.tag} series={s} />)
        )}
      </div>
    </section>
  );
}
