import type { RewardTerm } from "@rl-trainer-model";
import {
  REWARD_CATEGORY_HINTS,
  REWARD_PARAM_HINTS,
  REWARD_TERM_HINTS,
  clampRewardParam,
  getRewardCatalogEntry,
  getRewardParamRange,
} from "@rl-trainer-model";
import { Checkbox } from "../../components/Checkbox";
import { NumericInput } from "../../components/NumericInput";

function RewardParamRow({
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
      <NumericInput
        className="param-input reward-param-input"
        step={step}
        min={min}
        max={max}
        disabled={disabled}
        value={value}
        onCommit={onChange}
      />
    </div>
  );
}

function RewardTermCard({
  term,
  index,
  updateTerm,
  updateParam,
}: {
  term: RewardTerm;
  index: number;
  updateTerm: (index: number, patch: Partial<RewardTerm>) => void;
  updateParam: (index: number, key: string, value: number) => void;
}) {
  const catalog = getRewardCatalogEntry(term.id);
  const termHint = REWARD_TERM_HINTS[term.id] ?? REWARD_CATEGORY_HINTS[term.category];
  const categoryHint = REWARD_CATEGORY_HINTS[term.category];
  const weightRange = catalog
    ? {
        min: catalog.recommendedWeight < 0 ? catalog.recommendedWeight * 4 : 0,
        max: catalog.recommendedWeight < 0 ? 0 : catalog.recommendedWeight * 4,
        step: 0.01,
      }
    : { step: 0.01 };

  const applyRecommended = () => {
    if (!catalog) return;
    const params: Record<string, number> = {};
    for (const p of catalog.params) {
      params[p.key] = p.recommended;
    }
    updateTerm(index, { weight: catalog.recommendedWeight, params });
  };

  return (
    <article
      className={`reward-term-card inspector-param-card ${term.enabled ? "" : "term-inactive"}`}
      aria-label={`${term.type} term ${term.id}`}
    >
      <header className="reward-term-card-head">
        <Checkbox
          checked={term.enabled}
          onChange={(v) => updateTerm(index, { enabled: v })}
          hint={termHint}
        />
        <div className="reward-term-card-title">
          <span className="term-id" title={termHint}>
            {term.id.replace(/_/g, " ")}
          </span>
          <div className="reward-term-card-meta">
            <span className={`term-type term-${term.type}`}>{term.type}</span>
            <span className="term-category" title={categoryHint}>
              {term.category}
            </span>
            {catalog ? (
              <button
                type="button"
                className="reward-reset-btn"
                title="Reset weight and params to catalog recommendations"
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
        <RewardParamRow
          label="weight"
          hint={
            catalog
              ? `${REWARD_PARAM_HINTS.weight ?? ""} Recommended: ${catalog.recommendedWeight}`
              : REWARD_PARAM_HINTS.weight
          }
          value={term.weight}
          step={weightRange.step}
          min={weightRange.min}
          max={weightRange.max}
          disabled={!term.enabled}
          onChange={(v) => updateTerm(index, { weight: v })}
        />
        {Object.entries(term.params).map(([key, val]) => {
          const spec = getRewardParamRange(term.id, key);
          return (
            <RewardParamRow
              key={key}
              label={key}
              hint={
                spec
                  ? `${REWARD_PARAM_HINTS[key] ?? ""} Recommended: ${spec.recommended}`.trim()
                  : REWARD_PARAM_HINTS[key]
              }
              value={val}
              step={spec?.step ?? 0.01}
              min={spec?.min}
              max={spec?.max}
              disabled={!term.enabled}
              onChange={(v) =>
                updateParam(index, key, clampRewardParam(term.id, key, v))
              }
            />
          );
        })}
      </div>
    </article>
  );
}

export function RewardTermList({
  terms,
  onChange,
}: {
  terms: RewardTerm[];
  onChange: (terms: RewardTerm[]) => void;
}) {
  if (terms.length === 0) {
    return <p className="empty-desc">No reward/penalty terms configured for this stage.</p>;
  }

  const updateTerm = (index: number, patch: Partial<RewardTerm>) => {
    onChange(terms.map((t, i) => (i === index ? { ...t, ...patch } : t)));
  };

  const updateParam = (index: number, key: string, value: number) => {
    const term = terms[index];
    if (!term) return;
    updateTerm(index, { params: { ...term.params, [key]: value } });
  };

  const rewards = terms
    .map((t, i) => ({ term: t, index: i }))
    .filter(({ term }) => term.type === "reward");
  const penalties = terms
    .map((t, i) => ({ term: t, index: i }))
    .filter(({ term }) => term.type === "penalty");

  return (
    <div className="reward-penalty-panel">
      <section className="reward-penalty-section">
        <h4 className="reward-penalty-section-title">Rewards</h4>
        <div className="reward-penalty-section-grid">
          {rewards.map(({ term, index }) => (
            <RewardTermCard
              key={term.id}
              term={term}
              index={index}
              updateTerm={updateTerm}
              updateParam={updateParam}
            />
          ))}
        </div>
      </section>
      <section className="reward-penalty-section">
        <h4 className="reward-penalty-section-title">Penalties</h4>
        <div className="reward-penalty-section-grid">
          {penalties.map(({ term, index }) => (
            <RewardTermCard
              key={term.id}
              term={term}
              index={index}
              updateTerm={updateTerm}
              updateParam={updateParam}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
