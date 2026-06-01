import type { TerminationTerm } from "@rl-trainer-model";
import {
  TERMINATION_CATEGORY_HINTS,
  TERMINATION_PARAM_HINTS,
  TERMINATION_TERM_HINTS,
  clampTerminationParam,
  getTerminationCatalogEntry,
  getTerminationParamRange,
} from "@rl-trainer-model";
import { Checkbox } from "../../components/Checkbox";

function TerminationParamRow({
  label,
  hint,
  value,
  onChange,
  step = 0.01,
  min,
  max,
  disabled,
}: {
  label: string;
  hint?: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
  disabled?: boolean;
}) {
  const rangeHint =
    min !== undefined && max !== undefined ? ` [${min} … ${max}]` : "";
  const fullHint = hint ? `${hint}${rangeHint}` : rangeHint || undefined;

  return (
    <div className="reward-param-row">
      <label className="reward-param-label">
        <span>{label}</span>
        {fullHint ? (
          <span className="param-hint-icon" title={fullHint} aria-label={fullHint}>
            ⓘ
          </span>
        ) : null}
      </label>
      <input
        type="number"
        className="param-input reward-param-input"
        step={step}
        min={min}
        max={max}
        disabled={disabled}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}

function TerminationTermCard({
  term,
  index,
  updateTerm,
  updateParam,
  paramEnabled,
  onParamFlag,
}: {
  term: TerminationTerm;
  index: number;
  updateTerm: (index: number, patch: Partial<TerminationTerm>) => void;
  updateParam: (index: number, key: string, value: number) => void;
  paramEnabled?: (key: string, fallback?: boolean) => boolean;
  onParamFlag?: (key: string, enabled: boolean) => void;
}) {
  const catalog = getTerminationCatalogEntry(term.id);
  const label = catalog?.label ?? term.id.replace(/_/g, " ");
  const termHint = TERMINATION_TERM_HINTS[term.id] ?? TERMINATION_CATEGORY_HINTS[term.category];
  const categoryHint = TERMINATION_CATEGORY_HINTS[term.category];

  const applyRecommended = () => {
    if (!catalog) return;
    const params: Record<string, number> = {};
    for (const p of catalog.params) {
      params[p.key] = p.recommended;
    }
    updateTerm(index, { params });
  };

  const flagKey = (param: string) => `termination.${term.id}.${param}`;

  return (
    <article
      className={`reward-term-card inspector-param-card termination-term-card ${term.enabled ? "" : "term-inactive"}`}
      aria-label={`termination ${label}`}
    >
      <header className="reward-term-card-head">
        <Checkbox
          checked={term.enabled}
          onChange={(v) => updateTerm(index, { enabled: v })}
          hint={termHint}
        />
        <div className="reward-term-card-title">
          <span className="term-id" title={termHint}>
            {label}
          </span>
          <div className="reward-term-card-meta">
            <span className="term-type term-termination">termination</span>
            <span className="term-category" title={categoryHint}>
              {term.category}
            </span>
            {catalog ? (
              <button
                type="button"
                className="reward-reset-btn"
                title="Reset params to catalog recommendations"
                disabled={!term.enabled}
                onClick={applyRecommended}
              >
                ↺
              </button>
            ) : null}
          </div>
        </div>
      </header>

      <div className="reward-term-card-body">
        {Object.entries(term.params).map(([key, val]) => {
          const spec = getTerminationParamRange(term.id, key);
          const pKey = flagKey(key);
          const enabled = paramEnabled ? paramEnabled(pKey, term.enabled) : term.enabled;
          return (
            <TerminationParamRow
              key={key}
              label={key}
              hint={
                spec
                  ? `${TERMINATION_PARAM_HINTS[key] ?? ""} Recommended: ${spec.recommended}`.trim()
                  : TERMINATION_PARAM_HINTS[key]
              }
              value={val}
              step={spec?.step ?? 0.01}
              min={spec?.min}
              max={spec?.max}
              disabled={!term.enabled || !enabled}
              onChange={(v) => {
                if (onParamFlag && !paramEnabled?.(pKey)) {
                  onParamFlag(pKey, true);
                }
                updateParam(index, key, clampTerminationParam(term.id, key, v));
              }}
            />
          );
        })}
      </div>
    </article>
  );
}

export function TerminationTermList({
  terms,
  onChange,
  stage,
  onParamFlag,
}: {
  terms: TerminationTerm[];
  onChange: (terms: TerminationTerm[]) => void;
  stage?: { paramEnabled?: Record<string, boolean> };
  onParamFlag?: (key: string, enabled: boolean) => void;
}) {
  if (terms.length === 0) {
    return (
      <p className="empty-desc">No termination conditions in catalog — reload project to migrate.</p>
    );
  }

  const updateTerm = (index: number, patch: Partial<TerminationTerm>) => {
    onChange(terms.map((t, i) => (i === index ? { ...t, ...patch } : t)));
  };

  const updateParam = (index: number, key: string, value: number) => {
    const term = terms[index];
    if (!term) return;
    updateTerm(index, { params: { ...term.params, [key]: value } });
  };

  const paramEnabled = (key: string, fallback = true) => {
    if (!stage?.paramEnabled || !(key in stage.paramEnabled)) return fallback;
    return Boolean(stage.paramEnabled[key]);
  };

  const byCategory = new Map<string, { term: TerminationTerm; index: number }[]>();
  for (let i = 0; i < terms.length; i++) {
    const term = terms[i];
    if (!term) continue;
    const cat = term.category || "other";
    const list = byCategory.get(cat) ?? [];
    list.push({ term, index: i });
    byCategory.set(cat, list);
  }

  return (
    <div className="termination-conditions-panel">
      {[...byCategory.entries()].map(([category, items]) => (
        <section key={category} className="reward-penalty-section">
          <h4 className="reward-penalty-section-title" title={TERMINATION_CATEGORY_HINTS[category]}>
            {category}
          </h4>
          <div className="reward-penalty-section-grid">
            {items.map(({ term, index }) => (
              <TerminationTermCard
                key={term.id}
                term={term}
                index={index}
                updateTerm={updateTerm}
                updateParam={updateParam}
                paramEnabled={stage ? paramEnabled : undefined}
                onParamFlag={onParamFlag}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
