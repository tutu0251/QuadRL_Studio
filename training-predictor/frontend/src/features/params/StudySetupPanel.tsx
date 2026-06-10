import { NumberField } from "../../components/NumberField";
import { SectionCard } from "../../components/SectionCard";
import { SelectField } from "../../components/SelectField";
import { TextField } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";
import { SETUP_FIELDS } from "../../labels";
import { isRunning, useStudyStore } from "../../stores/studyStore";

/** The tuning-study setup form — every field named kindly, with its raw key beneath. */
export function StudySetupPanel() {
  const store = useStudyStore();
  const f = store.form;
  const locked = isRunning(store);
  const seq = f.mode === "sequential_stage";

  // Curriculum stages, chosen by NAME. `max_stages` is a prefix count over the
  // order-sorted stages, so each option's value is its 1-based position in the list.
  const hasCurriculum = store.curriculumEnabled && store.stages.length > 0;
  const stageOptions = hasCurriculum
    ? [
        { value: "", label: seq ? "All stages" : "All stages" },
        ...store.stages.map((s, i) => ({ value: String(i + 1), label: s.name })),
      ]
    : [{ value: "", label: "No curriculum in this project" }];

  // Resume a past study (global) or sequence (sequential) — or start fresh.
  const resumeOptions = seq
    ? [
        { value: "", label: "New sequence" },
        ...store.pastSequences.map((s) => ({
          value: s.seq_name,
          label: `${s.seq_name} · ${s.stages_done}/${s.stages_tuned} stages done`,
        })),
      ]
    : [
        { value: "", label: "New study" },
        ...store.pastStudies.map((s) => ({
          value: s.study_name,
          label:
            `${s.study_name} · ${s.n_trials} trial${s.n_trials === 1 ? "" : "s"}` +
            (s.best_value !== null ? ` · best ${s.best_value}` : ""),
        })),
      ];

  return (
    <SectionCard
      title="Study setup"
      meta={locked ? "Locked while running" : undefined}
      className="tp-setup"
    >
      <div className="tp-fieldgroup">
        <span className="qr-eyebrow">Tuning mode</span>
        <div className="qr-segmented tp-mode">
          <button
            type="button"
            className={`qr-segmented-btn ${!seq ? "active" : ""}`}
            disabled={locked}
            onClick={() => store.patchForm({ mode: "global", study_name: null })}
          >
            Single global study
          </button>
          <button
            type="button"
            className={`qr-segmented-btn ${seq ? "active" : ""}`}
            disabled={locked}
            onClick={() => store.patchForm({ mode: "sequential_stage", study_name: null })}
          >
            Sequential per-stage
          </button>
        </div>
        <p className="tp-modehint">
          {seq
            ? "Tune each curriculum stage separately and greedily — lock one stage, then warm-start the next from its best checkpoint. Each stage gets its own reward profile."
            : "One study, one shared parameter set across the whole run."}
        </p>
      </div>

      <div className="tp-fieldgroup">
        <span className="qr-eyebrow">The run</span>
        <SelectField
          meta={SETUP_FIELDS.study_name}
          value={f.study_name ?? ""}
          options={resumeOptions}
          disabled={locked}
          onChange={(v) => store.patchForm({ study_name: v === "" ? null : v })}
        />
        <div className="tp-grid-2">
          {seq ? (
            <>
              <NumberField
                meta={SETUP_FIELDS.trials_per_stage}
                value={f.trials_per_stage}
                min={1}
                max={200}
                step={1}
                disabled={locked}
                onChange={(v) => store.patchForm({ trials_per_stage: v ?? 1 })}
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
                meta={SETUP_FIELDS.timesteps_per_stage}
                value={f.timesteps_per_stage}
                min={1000}
                step={1000}
                disabled={locked}
                onChange={(v) => store.patchForm({ timesteps_per_stage: v ?? 1000 })}
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
            </>
          ) : (
            <>
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
            </>
          )}
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
          <SelectField
            meta={{
              ...SETUP_FIELDS.max_stages,
              label: seq ? "Tune Up To Stage" : SETUP_FIELDS.max_stages.label,
              hint: seq
                ? "Sequential mode tunes each stage from the first up to and including this one."
                : SETUP_FIELDS.max_stages.hint,
            }}
            value={f.max_stages === null ? "" : String(f.max_stages)}
            options={stageOptions}
            disabled={locked || !hasCurriculum}
            onChange={(v) => store.patchForm({ max_stages: v === "" ? null : parseInt(v, 10) })}
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

      {seq ? (
        <p className="tp-note">
          {hasCurriculum ? (
            <>
              Each selected stage's <em>reward weights &amp; shaping</em> are tuned against that
              stage's own objective; PPO hyperparameters stay fixed. Stages run one after another —
              "All stages" tunes the whole curriculum.
            </>
          ) : (
            <>This project has no curriculum, so there are no stages to tune sequentially. Pick a
              curriculum project or switch to a single global study.</>
          )}
        </p>
      ) : (
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
      )}
    </SectionCard>
  );
}
