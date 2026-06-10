import { NumberField } from "../../components/NumberField";
import { SectionCard } from "../../components/SectionCard";
import { TextField } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";
import { SETUP_FIELDS } from "../../labels";
import { isRunning, useStudyStore } from "../../stores/studyStore";

/** The tuning-study setup form — every field named kindly, with its raw key beneath. */
export function StudySetupPanel() {
  const store = useStudyStore();
  const f = store.form;
  const locked = isRunning(store);

  return (
    <SectionCard
      title="Study setup"
      meta={locked ? "Locked while running" : undefined}
      className="tp-setup"
    >
      <div className="tp-fieldgroup">
        <span className="qr-eyebrow">The run</span>
        <div className="tp-grid-2">
          <NumberField
            meta={SETUP_FIELDS.n_trials}
            value={f.n_trials}
            min={1}
            max={1000}
            step={1}
            disabled={locked}
            onChange={(v) => store.patchForm({ n_trials: v ?? 1 })}
          />
          <NumberField
            meta={SETUP_FIELDS.advisor_every_n}
            value={f.advisor_every_n}
            min={1}
            step={1}
            disabled={locked}
            onChange={(v) => store.patchForm({ advisor_every_n: v ?? 1 })}
          />
          <NumberField
            meta={SETUP_FIELDS.trial_timesteps}
            value={f.trial_timesteps}
            min={1000}
            step={1000}
            disabled={locked}
            onChange={(v) => store.patchForm({ trial_timesteps: v ?? 1000 })}
          />
          <NumberField
            meta={SETUP_FIELDS.trial_timeout}
            value={f.trial_timeout}
            min={1}
            step={10}
            nullable
            placeholder="no limit"
            disabled={locked}
            onChange={(v) => store.patchForm({ trial_timeout: v })}
          />
        </div>
      </div>

      <div className="tp-fieldgroup">
        <span className="qr-eyebrow">Simulation</span>
        <div className="tp-grid-2">
          <Toggle
            meta={SETUP_FIELDS.gazebo_headless}
            checked={f.gazebo_headless}
            disabled={locked}
            onChange={(v) => store.patchForm({ gazebo_headless: v })}
          />
          <Toggle
            meta={SETUP_FIELDS.mock_objective}
            checked={f.mock_objective}
            disabled={locked}
            onChange={(v) => store.patchForm({ mock_objective: v })}
          />
          <NumberField
            meta={SETUP_FIELDS.max_stages}
            value={f.max_stages}
            min={1}
            step={1}
            nullable
            placeholder="all stages"
            disabled={locked}
            onChange={(v) => store.patchForm({ max_stages: v })}
          />
          <TextField
            meta={SETUP_FIELDS.monitor_base_url}
            value={f.monitor_base_url}
            nullable
            placeholder="default (:8006)"
            disabled={locked}
            onChange={(v) => store.patchForm({ monitor_base_url: v })}
          />
        </div>
      </div>

      <div className="tp-fieldgroup">
        <span className="qr-eyebrow">What to tune</span>
        <div className="tp-grid-1">
          <Toggle
            meta={SETUP_FIELDS.include_hyperparams}
            checked={f.include_hyperparams}
            disabled={locked}
            onChange={(v) => store.patchForm({ include_hyperparams: v })}
          />
          <Toggle
            meta={SETUP_FIELDS.include_reward_weights}
            checked={f.include_reward_weights}
            disabled={locked}
            onChange={(v) => store.patchForm({ include_reward_weights: v })}
          />
          <Toggle
            meta={SETUP_FIELDS.include_reward_params}
            checked={f.include_reward_params}
            disabled={locked}
            onChange={(v) => store.patchForm({ include_reward_params: v })}
          />
        </div>
      </div>

      <p className="tp-note">
        Real trials run through the Train Monitor — the single training controller. Turn on{" "}
        <em>Practice Run</em> to exercise the loop with synthetic scores and no training.
      </p>
    </SectionCard>
  );
}
