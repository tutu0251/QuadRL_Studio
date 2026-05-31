import type { RewardTerm } from "@rl-trainer-model";
import { REWARD_CATEGORY_HINTS } from "@rl-trainer-model";
import { api } from "../../api/client";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";
import { useTrainerStore } from "../../stores/trainerStore";

export function RewardsPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);

  if (!model) return null;

  const saveTerms = async (terms: RewardTerm[]) => {
    if (!project) return;
    try {
      setModel(await api.patchModel(project, { rewardTerms: terms }));
    } catch (e) {
      log(String(e));
    }
  };

  const updateTerm = (index: number, patch: Partial<RewardTerm>) => {
    const terms = model.rewardTerms.map((t, i) => (i === index ? { ...t, ...patch } : t));
    void saveTerms(terms);
  };

  const updateParam = (index: number, key: string, value: number) => {
    const term = model.rewardTerms[index];
    if (!term) return;
    updateTerm(index, { params: { ...term.params, [key]: value } });
  };

  if (model.rewardTerms.length === 0) {
    return (
      <div className="tab-panel">
        <p className="empty-desc">No reward/penalty terms. Apply a preset or curriculum stage.</p>
      </div>
    );
  }

  return (
    <div className="tab-panel rewards-panel">
      {model.rewardTerms.map((term, i) => (
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
            <NumberField key={key} label={key} value={val} step={0.01} onChange={(v) => updateParam(i, key, v)} />
          ))}
        </div>
      ))}
    </div>
  );
}
