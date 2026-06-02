import { useEffect, useMemo, useState } from "react";
import {
  buildObservationVectorBreakdown,
  computeObservationFieldDim,
  computeObservationTermDim,
  formatObservationTermDimLabel,
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

const DEFAULT_N_JOINTS = 12;

function sensorAvailableFields(term: ObservationTerm): string[] {
  return term.availableFields?.length ? term.availableFields : term.fields ?? [];
}

function termForDimCalc(term: ObservationTerm): ObservationTerm {
  if (term.source !== "sensor") return term;
  const avail = sensorAvailableFields(term);
  return { ...term, fields: term.enabled ? (term.fields?.length ? term.fields : avail) : [] };
}

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
  dimLabel,
  onToggle,
  onPatch,
  onResetNorm,
  onToggleField,
}: {
  term: ObservationTerm;
  dimLabel: string;
  onToggle: (enabled: boolean) => void;
  onPatch: (patch: Partial<ObservationTerm>) => void;
  onResetNorm: () => void;
  onToggleField?: (field: string, checked: boolean) => void;
}) {
  const hint = OBSERVATION_KIND_HINTS[term.kind] ?? term.description ?? "";
  const unavailable = !term.available;
  const isSensor = term.source === "sensor";
  const hasClip = term.clipMin !== null || term.clipMax !== null;
  const inVector = term.enabled && term.available;

  return (
    <article
      className={`obs-term-card inspector-param-card ${inVector ? "obs-term-active" : "term-inactive"} ${unavailable ? "obs-unavailable" : ""}`}
      aria-label={`Observation ${term.label || term.key}`}
    >
      <header className="obs-term-card-head">
        <Checkbox
          checked={inVector}
          disabled={unavailable}
          onChange={onToggle}
          hint={hint}
        />
        <div className="obs-term-card-title">
          <div className="obs-term-title-row">
            <span className="term-id" title={hint}>
              {term.label || term.key}
            </span>
            <span
              className={`obs-dim-badge mono ${inVector ? "obs-dim-badge-active" : ""}`}
              title="Scalars in the policy observation vector"
            >
              {dimLabel}
            </span>
          </div>
          <div className="obs-term-card-meta">
            <span className="term-category">{term.kind}</span>
            <span className={`obs-source-badge obs-source-${term.source}`}>
              {isSensor ? "sensor" : "sim"}
            </span>
            {unavailable ? (
              <span className="obs-unavail-badge">not exported</span>
            ) : inVector ? (
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
            {term.fields && term.fields.length > 0 ? (
              <div className="obs-detail-wide">
                <dt>Selected fields</dt>
                <dd className="mono">{term.fields.join(", ")}</dd>
              </div>
            ) : null}
            {onToggleField && sensorAvailableFields(term).length > 0 && term.enabled ? (
              <div className="obs-detail-wide obs-field-picker">
                <dt>Fields</dt>
                <dd>
                  <ul className="obs-field-list compact">
                    {sensorAvailableFields(term).map((field) => {
                      const checked = (term.fields ?? []).includes(field);
                      const fd = computeObservationFieldDim(term.kind, field);
                      return (
                        <li key={field}>
                          <label className="obs-field-row">
                            <input
                              type="checkbox"
                              checked={checked}
                              disabled={unavailable}
                              onChange={(e) => onToggleField(field, e.target.checked)}
                            />
                            <span className="mono">{field}</span>
                            <span className="obs-field-dim">+{fd}</span>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                </dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p className="obs-term-desc">{term.description || hint}</p>
        )}

        <div className="obs-norm-collapsible">
          <CollapsibleSection
            id={`obs-norm-${term.id}`}
            title="Normalization"
            badge="scale · offset · clip"
            defaultOpen={false}
          >
          <div className="obs-norm-block-inner">
            <div className="obs-norm-block-head">
              <button
                type="button"
                className="reward-reset-btn"
                disabled={unavailable}
                title="Reset scale, offset, and clip to recommended values"
                onClick={onResetNorm}
              >
                Reset to recommended
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
          </CollapsibleSection>
        </div>
      </div>
    </article>
  );
}

function VectorBreakdownTable({
  segments,
}: {
  segments: ReturnType<typeof buildObservationVectorBreakdown>["segments"];
}) {
  const enabled = segments.filter((s) => s.startIndex !== null);
  if (enabled.length === 0) {
    return <p className="obs-vector-empty">No observations enabled — policy vector is empty.</p>;
  }

  return (
    <div className="obs-vector-table-wrap">
      <table className="obs-vector-table">
        <thead>
          <tr>
            <th scope="col">Index</th>
            <th scope="col">Term</th>
            <th scope="col">Dims</th>
            <th scope="col">Category</th>
          </tr>
        </thead>
        <tbody>
          {enabled.map((seg) => (
            <tr key={seg.termId}>
              <td className="mono obs-vector-index">
                {seg.startIndex}
                {seg.dim > 1 ? `–${(seg.startIndex ?? 0) + seg.dim - 1}` : ""}
              </td>
              <td>{seg.label}</td>
              <td className="mono">{seg.dim}</td>
              <td>
                <span className={`obs-cat-pill obs-cat-${seg.category}`}>{seg.category}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ObservationsPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const setObservationWizardOpen = useTrainerStore((s) => s.setObservationWizardOpen);
  const [filter, setFilter] = useState("");
  const [enabledOnly, setEnabledOnly] = useState(false);
  const [busy, setBusy] = useState<"recommend" | "sync" | null>(null);
  const [nJoints, setNJoints] = useState(DEFAULT_N_JOINTS);
  const [jointSource, setJointSource] = useState<"export" | "default">("default");

  const terms = model?.observationTerms ?? [];
  const query = filter.trim().toLowerCase();
  const dimCtx = useMemo(() => ({ nJoints }), [nJoints]);

  useEffect(() => {
    if (!project) return;
    let cancelled = false;
    api
      .getObservations(project)
      .then((summary) => {
        if (cancelled) return;
        const count = summary.jointCount ?? 0;
        if (count > 0) {
          setNJoints(count);
          setJointSource("export");
        } else {
          setNJoints(DEFAULT_N_JOINTS);
          setJointSource("default");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setNJoints(DEFAULT_N_JOINTS);
          setJointSource("default");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [project]);

  const breakdown = useMemo(
    () => buildObservationVectorBreakdown(terms.map(termForDimCalc), dimCtx),
    [terms, dimCtx]
  );

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
    const term = terms.find((t) => t.id === id);
    if (!term) return;
    if (term.source === "sensor" && enabled) {
      const avail = sensorAvailableFields(term);
      patchTerm(id, {
        enabled: true,
        fields: term.fields?.length ? term.fields : [...avail],
      });
      return;
    }
    if (term.source === "sensor" && !enabled) {
      patchTerm(id, { enabled: false, fields: [] });
      return;
    }
    patchTerm(id, { enabled });
  };

  const toggleSensorField = (id: string, field: string, checked: boolean) => {
    const term = terms.find((t) => t.id === id);
    if (!term || term.source !== "sensor") return;
    const avail = sensorAvailableFields(term);
    const next = new Set(term.fields ?? []);
    if (checked) next.add(field);
    else next.delete(field);
    const fields = avail.filter((f) => next.has(f));
    patchTerm(id, { enabled: fields.length > 0, fields });
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

  const termPassesFilter = (term: ObservationTerm) => {
    if (enabledOnly && (!term.enabled || !term.available)) return false;
    return matchesFilter(term, query);
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
            onClick={() => setObservationWizardOpen(true)}
          >
            Reconfigure step-by-step…
          </button>
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

      <section className="obs-vector-hero" aria-label="Policy observation vector size">
        <div className="obs-vector-hero-main">
          <span className="obs-vector-hero-label">Enabled observation dimensions</span>
          <span className="obs-vector-hero-value mono">{breakdown.totalDim}</span>
          <span className="obs-vector-hero-sub">
            {breakdown.enabledTermCount} term{breakdown.enabledTermCount === 1 ? "" : "s"} ·{" "}
            {stats.pct}% of catalog
            {jointSource === "export" ? (
              <> · {nJoints} joints from export</>
            ) : (
              <> · estimating {nJoints} joints (export ctrl gains)</>
            )}
          </span>
        </div>
        <div className="obs-vector-chips" role="list">
          {CATEGORY_ORDER.map((cat) => {
            const d = breakdown.categoryDims[cat] ?? 0;
            return (
              <span
                key={cat}
                className={`obs-vector-chip obs-cat-${cat} ${d === 0 ? "obs-vector-chip-empty" : ""}`}
                role="listitem"
              >
                <span className="obs-vector-chip-label">{CATEGORY_LABELS[cat]}</span>
                <span className="obs-vector-chip-value mono">{d}</span>
              </span>
            );
          })}
        </div>
      </section>

      <div className="obs-toolbar">
        <div className="obs-metrics">
          <MetricCard
            label="Terms"
            value={`${stats.enabled.length}/${stats.available.length}`}
            sub="enabled / available"
            variant="accent"
          />
          <MetricCard
            label="State dims"
            value={String(breakdown.categoryDims.state ?? 0)}
            sub="procedural"
          />
          <MetricCard
            label="Command dims"
            value={String(breakdown.categoryDims.command ?? 0)}
            sub="reference"
          />
          <MetricCard
            label="Sensor dims"
            value={String(breakdown.categoryDims.sensor ?? 0)}
            sub="ROS bridged"
          />
        </div>

        <div className="obs-breakdown-section">
          <CollapsibleSection
            id="obs-vector-breakdown"
            title="Vector layout"
            badge={`${breakdown.totalDim} dims`}
            defaultOpen
          >
            <p className="obs-breakdown-desc">
              Concatenation order matches the training env: enabled terms only, in catalog order.
            </p>
            <VectorBreakdownTable segments={breakdown.segments} />
          </CollapsibleSection>
        </div>

        <details className="obs-norm-details">
          <summary>Normalization formula</summary>
          <p className="obs-norm-formula-banner">{OBSERVATION_NORM_FORMULA}</p>
        </details>

        <div className="obs-filter-row">
          <input
            type="search"
            className="obs-filter-input field-input"
            placeholder="Filter by name, kind, topic…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Filter observations"
          />
          <label className="obs-enabled-only">
            <input
              type="checkbox"
              checked={enabledOnly}
              onChange={(e) => setEnabledOnly(e.target.checked)}
            />
            Enabled only
          </label>
        </div>
      </div>

      <div className="obs-cards-scroll editor-scroll">
        {CATEGORY_ORDER.map((category) => {
          const group = (groups.get(category) ?? []).filter((t) => termPassesFilter(t));
          if (group.length === 0) return null;

          const catEnabled = group.filter((t) => t.enabled && t.available).length;
          const catAvailable = group.filter((t) => t.available).length;
          const catDims = group
            .filter((t) => t.enabled && t.available)
            .reduce((sum, t) => sum + computeObservationTermDim(t, dimCtx), 0);
          const catHint = OBSERVATION_CATEGORY_HINTS[category];

          return (
            <CollapsibleSection
              key={category}
              id={`obs-${category}`}
              title={CATEGORY_LABELS[category]}
              badge={`${catEnabled}/${catAvailable} · ${catDims}d`}
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
                    dimLabel={formatObservationTermDimLabel(
                      {
                        ...term,
                        fields:
                          term.source === "sensor" && term.enabled
                            ? term.fields ?? sensorAvailableFields(term)
                            : term.fields,
                      },
                      dimCtx
                    )}
                    onToggle={(enabled) => toggleTerm(term.id, enabled)}
                    onPatch={(patch) => patchTerm(term.id, patch)}
                    onResetNorm={() => resetNorm(term.id)}
                    onToggleField={
                      term.source === "sensor" ? (field, checked) => toggleSensorField(term.id, field, checked) : undefined
                    }
                  />
                ))}
              </div>
            </CollapsibleSection>
          );
        })}

        {CATEGORY_ORDER.every(
          (cat) => (groups.get(cat) ?? []).filter((t) => termPassesFilter(t)).length === 0
        ) && (
          <div className="editor-empty-state compact">
            <p className="empty-desc">
              {enabledOnly && !query
                ? "No enabled observations — enable terms above or turn off “Enabled only”."
                : `No observations match your filters.`}
            </p>
            <div className="obs-empty-actions">
              {enabledOnly ? (
                <button
                  type="button"
                  className="header-btn compact"
                  onClick={() => setEnabledOnly(false)}
                >
                  Show all
                </button>
              ) : null}
              {query ? (
                <button type="button" className="header-btn compact" onClick={() => setFilter("")}>
                  Clear search
                </button>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
