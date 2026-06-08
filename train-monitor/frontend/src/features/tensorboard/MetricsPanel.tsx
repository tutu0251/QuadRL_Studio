import { useEffect, useId, useMemo, useState, type CSSProperties } from "react";
import { api, getApiBaseUrl, tbOpenUrl } from "../../api/client";
import { ActionButton } from "../../components/ActionButton";
import type { RunStageInfo, ScalarSeries, TensorBoardStatus } from "../../types";

type Props = {
  project: string | null;
  runId: string | null;
  scalars: ScalarSeries[];
  stages: RunStageInfo[];
  curriculumEnabled: boolean;
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

const TB_COLORS = ["#5b8def", "#34c6c6", "#46c98b", "#e0a942", "#ef6f6f", "#b48ef0"];

/** Show core RL metrics first (matches training/scripts/tb_callbacks.py). */
const FUNDAMENTAL_PREFIXES = ["rollout/", "eval/", "train/", "time/"];

const GROUP_LABELS: Record<string, string> = {
  "rollout/": "Rollout",
  "eval/": "Eval",
  "train/": "Train",
  "time/": "Time",
};

function scalarSortKey(tag: string): [number, string] {
  const idx = FUNDAMENTAL_PREFIXES.findIndex((p) => tag.startsWith(p));
  return [idx === -1 ? FUNDAMENTAL_PREFIXES.length : idx, tag];
}

/** Group tag → display label and the leaf name shown in the metric list. */
function tagGroup(tag: string): string {
  const slash = tag.indexOf("/");
  if (slash === -1) return "Other";
  return GROUP_LABELS[tag.slice(0, slash + 1)] ?? tag.slice(0, slash);
}

function tagLeaf(tag: string): string {
  const slash = tag.indexOf("/");
  return slash === -1 ? tag : tag.slice(slash + 1);
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
  runId,
  scalars,
  stages,
  curriculumEnabled,
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

  // Stage sub-tabs: only the curriculum stages that actually have event files.
  const stageTabs = useMemo(
    () => (curriculumEnabled ? stages.filter((s) => s.has_events) : []),
    [curriculumEnabled, stages],
  );

  // activeStage === null → "Combined" (all stages merged, the `scalars` prop).
  const [activeStage, setActiveStage] = useState<string | null>(null);
  const [stageScalars, setStageScalars] = useState<ScalarSeries[]>([]);
  const [stageLoading, setStageLoading] = useState(false);

  // Reset to the combined view when the run changes or stages disappear.
  useEffect(() => {
    setActiveStage(null);
  }, [runId]);

  useEffect(() => {
    if (activeStage && !stageTabs.some((s) => s.name === activeStage)) {
      setActiveStage(null);
    }
  }, [activeStage, stageTabs]);

  // Fetch the selected stage's scalars. Re-fetches when the parent refreshes
  // `scalars` (its polling proxy) so a selected stage also updates live.
  useEffect(() => {
    if (!project || !runId || !activeStage) {
      setStageScalars([]);
      return;
    }
    let cancelled = false;
    setStageLoading(true);
    api
      .getScalars(project, runId, activeStage)
      .then((r) => {
        if (!cancelled) setStageScalars(r.series);
      })
      .catch(() => {
        if (!cancelled) setStageScalars([]);
      })
      .finally(() => {
        if (!cancelled) setStageLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [project, runId, activeStage, scalars]);

  const activeScalars = activeStage ? stageScalars : scalars;

  const sortedScalars = useMemo(
    () =>
      [...activeScalars].sort((a, b) => {
        const [pa, ta] = scalarSortKey(a.tag);
        const [pb, tb] = scalarSortKey(b.tag);
        return pa !== pb ? pa - pb : ta.localeCompare(tb);
      }),
    [activeScalars],
  );

  // Metric list selection: track HIDDEN tags so new tags appear by default.
  const [hiddenTags, setHiddenTags] = useState<Set<string>>(new Set());
  const toggleTag = (tag: string) =>
    setHiddenTags((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  const showAll = () => setHiddenTags(new Set());
  const hideAll = () => setHiddenTags(new Set(sortedScalars.map((s) => s.tag)));

  const visibleScalars = sortedScalars.filter((s) => !hiddenTags.has(s.tag));

  // Group the available tags for the metric list.
  const groups = useMemo(() => {
    const map = new Map<string, ScalarSeries[]>();
    for (const s of sortedScalars) {
      const g = tagGroup(s.tag);
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(s);
    }
    return [...map.entries()];
  }, [sortedScalars]);

  const hasData = sortedScalars.length > 0;

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

      {stageTabs.length > 0 && (
        <div className="metric-stage-tabs qr-segmented" role="tablist" aria-label="Curriculum stage">
          <button
            type="button"
            role="tab"
            aria-selected={activeStage === null}
            className={`qr-segmented-btn ${activeStage === null ? "active" : ""}`}
            onClick={() => setActiveStage(null)}
          >
            Combined
          </button>
          {stageTabs.map((s) => (
            <button
              key={s.name}
              type="button"
              role="tab"
              aria-selected={activeStage === s.name}
              className={`qr-segmented-btn ${activeStage === s.name ? "active" : ""}`}
              onClick={() => setActiveStage(s.name)}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}

      <div className="metrics-body">
        <aside className="metric-tag-list" aria-label="Metric selection">
          <div className="metric-tag-list-head">
            <span className="qr-eyebrow">
              Metrics
              <span className="metric-tag-count">
                {visibleScalars.length}/{sortedScalars.length}
              </span>
            </span>
            <div className="metric-tag-list-actions">
              <button type="button" className="btn tiny ghost" onClick={showAll} disabled={!hasData}>
                All
              </button>
              <button type="button" className="btn tiny ghost" onClick={hideAll} disabled={!hasData}>
                None
              </button>
            </div>
          </div>
          <div className="metric-tag-list-scroll">
            {!hasData ? (
              <p className="metric-tag-empty">No metrics</p>
            ) : (
              groups.map(([label, items]) => (
                <div key={label} className="metric-tag-group">
                  <div className="qr-eyebrow metric-tag-group-label">{label}</div>
                  {items.map((s) => {
                    const colorIndex = sortedScalars.indexOf(s);
                    return (
                      <label
                        key={s.tag}
                        className="metric-tag-row"
                        title={s.tag}
                        style={{ "--chart-color": TB_COLORS[colorIndex % TB_COLORS.length] } as CSSProperties}
                      >
                        <input
                          type="checkbox"
                          checked={!hiddenTags.has(s.tag)}
                          onChange={() => toggleTag(s.tag)}
                        />
                        <span className="metric-tag-swatch" />
                        <span className="metric-tag-name">{tagLeaf(s.tag) || s.tag}</span>
                        <span className="metric-tag-val">
                          {s.values.length ? s.values[s.values.length - 1].toPrecision(3) : "—"}
                        </span>
                      </label>
                    );
                  })}
                </div>
              ))
            )}
          </div>
        </aside>

        <div className="tb-chart-grid">
          {stageLoading && activeStage && !hasData ? (
            <p className="panel-hint metrics-empty">Loading {activeStage} metrics…</p>
          ) : !hasData ? (
            <p className="panel-hint metrics-empty">
              {trainingActive
                ? "Waiting for metrics — PPO logs one point per rollout (~2k env steps). With the ROS sim this is often 1–2 minutes before the first chart appears."
                : "No scalar metrics yet — start training or select a run with TensorBoard event files."}
            </p>
          ) : visibleScalars.length === 0 ? (
            <p className="panel-hint metrics-empty">
              All metrics hidden — enable some in the Metrics list on the left.
            </p>
          ) : (
            visibleScalars.map((s) => (
              <TensorBoardChart key={s.tag} series={s} colorIndex={sortedScalars.indexOf(s)} />
            ))
          )}
        </div>
      </div>
    </section>
  );
}
