import { useMemo, useState } from "react";
import {
  getRecommendedObservationNorm,
  OBSERVATION_CATEGORY_HINTS,
  OBSERVATION_KIND_HINTS,
  OBSERVATION_NORM_FORMULA,
  OBSERVATION_NORM_HINTS,
  type ObservationTerm,
} from "@rl-trainer-model";
import { api } from "../../api/client";
import { Checkbox } from "../../components/Checkbox";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { MetricCard } from "../../components/MetricCard";
import { NumberField } from "../../components/NumberField";
import { useTrainerStore } from "../../stores/trainerStore";

const CATEGORY_ORDER = ["state", "command", "sensor"] as const;

const CATEGORY_LABELS: Record<(typeof CATEGORY_ORDER)[number], string> = {
  state: "Procedural state",
  command: "Command reference",
  sensor: "ROS sensors",
};

function groupTerms(terms: ObservationTerm[]): Map<string, ObservationTerm[]> {
  const groups = new Map<string, ObservationTerm[]>();
  for (const cat of CATEGORY_ORDER) {
    groups.set(cat, []);
  }
  for (const term of terms) {
    const cat = term.category || "sensor";
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(term);
  }
  return groups;
}

function matchesFilter(term: ObservationTerm, query: string): boolean {
  if (!query) return true;
  const hay = [
    term.label,
    term.key,
    term.kind,
    term.topic,
    term.parentLink,
    term.description,
    String(term.scale),
    ...(term.fields ?? []),
  ]
    .join(" ")
    .toLowerCase();
  return hay.includes(query);
}

function OptionalClipField({
  label,
  hint,
  value,
  onChange,
  disabled,
}: {
  label: string;
  hint?: string;
  value: number | null;
  onChange: (v: number | null) => void;
  disabled?: boolean;
}) {
  return (
    <div className="param-field obs-clip-field">
      <span className="param-label-row">
        <span className="param-label" title={hint}>
          {label}
        </span>
        {hint ? (
          <span className="param-hint-icon" title={hint} aria-label={hint}>
            ⓘ
          </span>
        ) : null}
      </span>
      <input
        type="number"
        className="param-input"
        step={0.1}
        disabled={disabled}
        placeholder="none"
        value={value === null || value === undefined ? "" : value}
        onChange={(e) => {
          const raw = e.target.value.trim();
          if (raw === "") {
            onChange(null);
            return;
          }
          const n = parseFloat(raw);
          onChange(Number.isFinite(n) ? n : null);
        }}
      />
    </div>
  );
}

function ObservationCard({
  term,
  onToggle,
  onPatch,
  onResetNorm,
}: {
  term: ObservationTerm;
  onToggle: (enabled: boolean) => void;
  onPatch: (patch: Partial<ObservationTerm>) => void;
  onResetNorm: () => void;
}) {
  const hint = OBSERVATION_KIND_HINTS[term.kind] ?? term.description ?? "";
  const unavailable = !term.available;
  const isSensor = term.source === "sensor";
  const hasClip = term.clipMin !== null || term.clipMax !== null;

  return (
    <article
      className={`obs-term-card inspector-param-card ${term.enabled && term.available ? "" : "term-inactive"} ${unavailable ? "obs-unavailable" : ""}`}
      aria-label={`Observation ${term.label || term.key}`}
    >
      <header className="obs-term-card-head">
        <Checkbox
          checked={term.enabled && term.available}
          disabled={unavailable}
          onChange={onToggle}
          hint={hint}
        />
        <div className="obs-term-card-title">
          <span className="term-id" title={hint}>
            {term.label || term.key}
          </span>
          <div className="obs-term-card-meta">
            <span className="term-category">{term.kind}</span>
            <span className={`obs-source-badge obs-source-${term.source}`}>
              {isSensor ? "sensor" : "sim"}
            </span>
            {unavailable ? (
              <span className="obs-unavail-badge">not exported</span>
            ) : term.enabled ? (
              <span className="obs-active-badge">in vector</span>
            ) : null}
            {!unavailable && term.scale > 0 ? (
              <span className="obs-norm-badge mono" title={OBSERVATION_NORM_FORMULA}>
                ÷{term.scale.toFixed(2)}
                {hasClip ? ` · clip` : ""}
              </span>
            ) : null}
          </div>
        </div>
      </header>

      <div className="obs-term-card-body">
        {isSensor ? (
          <dl className="obs-detail-list obs-detail-compact">
            <div>
              <dt>Link</dt>
              <dd>{term.parentLink || "—"}</dd>
            </div>
            <div className="obs-detail-wide">
              <dt>Topic</dt>
              <dd className="mono">{term.topic || "—"}</dd>
            </div>
          </dl>
        ) : (
          <p className="obs-term-desc">{term.description || hint}</p>
        )}

        <div className="obs-norm-block">
          <div className="obs-norm-block-head">
            <span className="obs-norm-block-title">Normalization</span>
            <button
              type="button"
              className="reward-reset-btn"
              disabled={unavailable}
              title="Reset scale, offset, and clip to recommended values"
              onClick={onResetNorm}
            >
              Reset
            </button>
          </div>
          <div className="obs-norm-grid">
            <NumberField
              label="scale"
              hint={OBSERVATION_NORM_HINTS.scale}
              value={term.scale}
              step={0.01}
              min={0.001}
              disabled={unavailable}
              onChange={(v) => onPatch({ scale: Math.max(v, 0.001) })}
            />
            <NumberField
              label="offset"
              hint={OBSERVATION_NORM_HINTS.offset}
              value={term.offset}
              step={0.01}
              disabled={unavailable}
              onChange={(v) => onPatch({ offset: v })}
            />
            <OptionalClipField
              label="clip min"
              hint={OBSERVATION_NORM_HINTS.clipMin}
              value={term.clipMin}
              disabled={unavailable}
              onChange={(clipMin) => onPatch({ clipMin })}
            />
            <OptionalClipField
              label="clip max"
              hint={OBSERVATION_NORM_HINTS.clipMax}
              value={term.clipMax}
              disabled={unavailable}
              onChange={(clipMax) => onPatch({ clipMax })}
            />
          </div>
        </div>
      </div>
    </article>
  );
}

export function ObservationsPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState<"recommend" | "sync" | null>(null);

  const terms = model?.observationTerms ?? [];
  const query = filter.trim().toLowerCase();

  const stats = useMemo(() => {
    const available = terms.filter((t) => t.available);
    const enabled = available.filter((t) => t.enabled);
    const procedural = enabled.filter((t) => t.source === "procedural").length;
    const sensors = enabled.filter((t) => t.source === "sensor").length;
    const pct =
      available.length > 0 ? Math.round((enabled.length / available.length) * 100) : 0;
    return { available, enabled, procedural, sensors, pct, total: terms.length };
  }, [terms]);

  const groups = useMemo(() => groupTerms(terms), [terms]);

  if (!model || !project) return null;

  const saveTerms = async (next: ObservationTerm[]) => {
    try {
      setModel(await api.patchModel(project, { observationTerms: next }));
    } catch (e) {
      log(String(e));
    }
  };

  const patchTerm = (id: string, patch: Partial<ObservationTerm>) => {
    const next = terms.map((t) => (t.id === id ? { ...t, ...patch } : t));
    void saveTerms(next);
  };

  const toggleTerm = (id: string, enabled: boolean) => {
    patchTerm(id, { enabled });
  };

  const resetNorm = (id: string) => {
    const term = terms.find((t) => t.id === id);
    if (!term) return;
    const d = getRecommendedObservationNorm(term);
    patchTerm(id, {
      scale: d.scale,
      offset: d.offset,
      clipMin: d.clipMin,
      clipMax: d.clipMax,
    });
  };

  const setGroupEnabled = (category: string, enabled: boolean) => {
    const next = terms.map((t) =>
      t.category === category && t.available ? { ...t, enabled } : t
    );
    void saveTerms(next);
  };

  const recommend = async () => {
    setBusy("recommend");
    try {
      setModel(await api.recommendObservations(project));
      log("Applied recommended observation selection and normalization");
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(null);
    }
  };

  const syncCatalog = async () => {
    setBusy("sync");
    try {
      setModel(await api.syncObservations(project));
      log("Refreshed observation catalog from sensor model");
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(null);
    }
  };

  if (terms.length === 0) {
    return (
      <div className="tab-panel observations-panel">
        <div className="observations-empty editor-empty-state">
          <div className="editor-empty-icon" aria-hidden>
            ◎
          </div>
          <h2>No observation catalog</h2>
          <p>
            Configure sensors in the Sensor Editor, then refresh here to build the full
            observation list.
          </p>
          <ol className="workflow-steps compact-workflow">
            <li>Sensor Editor → import ctrl URDF</li>
            <li>Bootstrap or add IMU + contacts</li>
            <li>Export RL package</li>
          </ol>
          <button
            type="button"
            className="header-btn primary"
            disabled={busy === "sync"}
            onClick={() => void syncCatalog()}
          >
            {busy === "sync" ? "Refreshing…" : "Refresh catalog"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-panel observations-panel">
      <div className="pane-header pane-header-actions obs-pane-header">
        <div>
          <h4 className="pane-title">Observations</h4>
          <span className="pane-subtitle">
            Policy input · <code className="mono">sens_{project}_observations.yaml</code>
          </span>
        </div>
        <div className="obs-header-actions">
          <button
            type="button"
            className="header-btn"
            disabled={busy !== null}
            onClick={() => void syncCatalog()}
          >
            {busy === "sync" ? "…" : "Refresh"}
          </button>
          <button
            type="button"
            className="header-btn primary"
            disabled={busy !== null}
            onClick={() => void recommend()}
          >
            {busy === "recommend" ? "…" : "Recommend"}
          </button>
        </div>
      </div>

      <div className="obs-toolbar">
        <div className="obs-metrics">
          <MetricCard
            label="Selected"
            value={`${stats.enabled.length}/${stats.available.length}`}
            sub={`${stats.pct}% of available`}
            variant="accent"
          />
          <MetricCard label="Procedural" value={String(stats.procedural)} sub="sim / wrapper" />
          <MetricCard label="Sensors" value={String(stats.sensors)} sub="ROS topics" />
          <MetricCard label="Catalog" value={String(stats.total)} sub="total entries" />
        </div>
        <p className="obs-norm-formula-banner" title={OBSERVATION_NORM_FORMULA}>
          {OBSERVATION_NORM_FORMULA}
        </p>
        <div className="obs-progress-wrap">
          <div
            className="obs-progress-bar"
            role="progressbar"
            aria-valuenow={stats.pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Observation selection coverage"
          >
            <div className="obs-progress-fill" style={{ width: `${stats.pct}%` }} />
          </div>
        </div>
        <input
          type="search"
          className="obs-filter-input field-input"
          placeholder="Filter by name, kind, topic…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filter observations"
        />
      </div>

      <div className="obs-cards-scroll editor-scroll">
        {CATEGORY_ORDER.map((category) => {
          const group = (groups.get(category) ?? []).filter((t) => matchesFilter(t, query));
          if (group.length === 0) return null;

          const catEnabled = group.filter((t) => t.enabled && t.available).length;
          const catAvailable = group.filter((t) => t.available).length;
          const catHint = OBSERVATION_CATEGORY_HINTS[category];

          return (
            <CollapsibleSection
              key={category}
              id={`obs-${category}`}
              title={CATEGORY_LABELS[category]}
              badge={`${catEnabled}/${catAvailable}`}
              defaultOpen
            >
              <div className="obs-section-toolbar">
                {catHint ? <p className="obs-section-hint">{catHint}</p> : null}
                <div className="obs-section-actions">
                  <button
                    type="button"
                    className="header-btn compact"
                    onClick={() => setGroupEnabled(category, true)}
                  >
                    Select all
                  </button>
                  <button
                    type="button"
                    className="header-btn compact"
                    onClick={() => setGroupEnabled(category, false)}
                  >
                    Clear
                  </button>
                </div>
              </div>
              <div className="obs-cards-grid">
                {group.map((term) => (
                  <ObservationCard
                    key={term.id}
                    term={term}
                    onToggle={(enabled) => toggleTerm(term.id, enabled)}
                    onPatch={(patch) => patchTerm(term.id, patch)}
                    onResetNorm={() => resetNorm(term.id)}
                  />
                ))}
              </div>
            </CollapsibleSection>
          );
        })}

        {CATEGORY_ORDER.every(
          (cat) => (groups.get(cat) ?? []).filter((t) => matchesFilter(t, query)).length === 0
        ) && (
          <div className="editor-empty-state compact">
            <p className="empty-desc">No observations match &ldquo;{filter}&rdquo;</p>
            <button type="button" className="header-btn compact" onClick={() => setFilter("")}>
              Clear filter
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
