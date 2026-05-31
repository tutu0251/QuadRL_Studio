import type { RewardTerm } from "@rl-trainer-model";
import {
  REWARD_CATEGORY_HINTS,
  REWARD_PARAM_HINTS,
  REWARD_TERM_HINTS,
} from "@rl-trainer-model";
import { Checkbox } from "../../components/Checkbox";

function RewardParamRow({
  label,
  hint,
  value,
  onChange,
  step = 0.01,
  disabled,
}: {
  label: string;
  hint?: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  disabled?: boolean;
}) {
  return (
    <div className="reward-param-row">
      <label className="reward-param-label">
        <span>{label}</span>
        {hint ? (
          <span className="param-hint-icon" title={hint} aria-label={hint}>
            ⓘ
          </span>
        ) : null}
      </label>
      <input
        type="number"
        className="param-input reward-param-input"
        step={step}
        disabled={disabled}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
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
    return <p className="empty-desc">No reward terms configured for this stage.</p>;
  }

  const updateTerm = (index: number, patch: Partial<RewardTerm>) => {
    onChange(terms.map((t, i) => (i === index ? { ...t, ...patch } : t)));
  };

  const updateParam = (index: number, key: string, value: number) => {
    const term = terms[index];
    if (!term) return;
    updateTerm(index, { params: { ...term.params, [key]: value } });
  };

  return (
    <>
      {terms.map((term, i) => {
        const termHint = REWARD_TERM_HINTS[term.id] ?? REWARD_CATEGORY_HINTS[term.category];
        const categoryHint = REWARD_CATEGORY_HINTS[term.category];

        return (
          <article
            key={term.id}
            className={`reward-term-card inspector-param-card ${term.enabled ? "" : "term-inactive"}`}
            aria-label={`Reward term ${term.id}`}
          >
            <header className="reward-term-card-head">
              <Checkbox
                checked={term.enabled}
                onChange={(v) => updateTerm(i, { enabled: v })}
                hint={termHint}
              />
              <div className="reward-term-card-title">
                <span className="term-id" title={termHint}>
                  {term.id}
                </span>
                <div className="reward-term-card-meta">
                  <span className={`term-type term-${term.type}`}>{term.type}</span>
                  <span className="term-category" title={categoryHint}>
                    {term.category}
                  </span>
                </div>
              </div>
            </header>

            <div className="reward-term-card-body">
              <RewardParamRow
                label="weight"
                hint={REWARD_PARAM_HINTS.weight}
                value={term.weight}
                step={0.01}
                disabled={!term.enabled}
                onChange={(v) => updateTerm(i, { weight: v })}
              />
              {Object.entries(term.params).map(([key, val]) => (
                <RewardParamRow
                  key={key}
                  label={key}
                  hint={REWARD_PARAM_HINTS[key]}
                  value={val}
                  step={0.01}
                  disabled={!term.enabled}
                  onChange={(v) => updateParam(i, key, v)}
                />
              ))}
            </div>
          </article>
        );
      })}
    </>
  );
}
