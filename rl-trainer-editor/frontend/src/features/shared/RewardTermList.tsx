import type { RewardTerm } from "@rl-trainer-model";
import { REWARD_CATEGORY_HINTS } from "@rl-trainer-model";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";

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
    <div className="reward-term-list">
      {terms.map((term, i) => (
        <div key={term.id} className="reward-term-card">
          <div className="reward-term-header">
            <Toggle
              label={term.id}
              checked={term.enabled}
              onChange={(v) => updateTerm(i, { enabled: v })}
            />
            <span className={`term-type term-${term.type}`}>{term.type}</span>
            <span className="term-category" title={REWARD_CATEGORY_HINTS[term.category]}>
              {term.category}
            </span>
          </div>
          <NumberField
            label="weight"
            value={term.weight}
            step={0.01}
            onChange={(v) => updateTerm(i, { weight: v })}
          />
          {Object.entries(term.params).map(([key, val]) => (
            <NumberField
              key={key}
              label={key}
              value={val}
              step={0.01}
              onChange={(v) => updateParam(i, key, v)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
