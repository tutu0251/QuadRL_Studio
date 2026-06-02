import { useMemo, useState } from "react";
import {
  buildObservationVectorBreakdown,
  computeObservationFieldDim,
  computeObservationTermDim,
  formatObservationTermDimLabel,
  OBSERVATION_CATEGORY_HINTS,
  OBSERVATION_KIND_HINTS,
  type ObservationTerm,
} from "@rl-trainer-model";
import { Checkbox } from "../../components/Checkbox";

const CATEGORY_ORDER = ["state", "command", "sensor"] as const;

const CATEGORY_LABELS: Record<(typeof CATEGORY_ORDER)[number], string> = {
  state: "Procedural state",
  command: "Command reference",
  sensor: "ROS sensors",
};

export function orderObservationTerms(terms: ObservationTerm[]): ObservationTerm[] {
  const rank = new Map(CATEGORY_ORDER.map((c, i) => [c, i]));
  return terms
    .map((t, i) => ({ t, i }))
    .sort((a, b) => {
      const ca = rank.get((a.t.category || "sensor") as (typeof CATEGORY_ORDER)[number]) ?? 99;
      const cb = rank.get((b.t.category || "sensor") as (typeof CATEGORY_ORDER)[number]) ?? 99;
      if (ca !== cb) return ca - cb;
      return a.i - b.i;
    })
    .map(({ t }) => t);
}

function sensorAvailableFields(term: ObservationTerm): string[] {
  return term.availableFields?.length ? term.availableFields : term.fields ?? [];
}

function termForDim(term: ObservationTerm): ObservationTerm {
  if (term.source !== "sensor") return term;
  const avail = sensorAvailableFields(term);
  return { ...term, fields: term.enabled ? term.fields ?? avail : [] };
}

type Props = {
  terms: ObservationTerm[];
  nJoints: number;
  onConfirm: (terms: ObservationTerm[]) => void;
  onDismiss: () => void;
};

export function ObservationSetupWizard({ terms, nJoints, onConfirm, onDismiss }: Props) {
  const ordered = useMemo(() => orderObservationTerms(terms), [terms]);
  const [draft, setDraft] = useState<ObservationTerm[]>(() =>
    ordered.map((t) => ({
      ...t,
      fields:
        t.source === "sensor" && t.enabled
          ? [...(t.fields?.length ? t.fields : sensorAvailableFields(t))]
          : t.fields,
    }))
  );
  const [step, setStep] = useState(0);
  const dimCtx = useMemo(() => ({ nJoints }), [nJoints]);
  const reviewStep = draft.length;
  const onReview = step >= reviewStep;
  const current = !onReview ? draft[step] : null;

  const breakdown = useMemo(
    () => buildObservationVectorBreakdown(draft.map(termForDim), dimCtx),
    [draft, dimCtx]
  );

  const patchTerm = (id: string, patch: Partial<ObservationTerm>) => {
    setDraft((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
  };

  const setIncluded = (term: ObservationTerm, included: boolean) => {
    if (!term.available) return;
    if (term.source === "sensor") {
      const avail = sensorAvailableFields(term);
      patchTerm(term.id, {
        enabled: included,
        fields: included ? (term.fields?.length ? term.fields : [...avail]) : [],
      });
      return;
    }
    patchTerm(term.id, { enabled: included });
  };

  const toggleField = (term: ObservationTerm, field: string, checked: boolean) => {
    const avail = sensorAvailableFields(term);
    const currentFields = new Set(term.fields ?? []);
    if (checked) currentFields.add(field);
    else currentFields.delete(field);
    const next = [...avail.filter((f) => currentFields.has(f))];
    patchTerm(term.id, {
      enabled: next.length > 0,
      fields: next,
    });
  };

  const goNext = () => setStep((s) => Math.min(s + 1, reviewStep));
  const goBack = () => setStep((s) => Math.max(s - 1, 0));

  return (
    <div className="obs-wizard-overlay" role="presentation">
      <div
        className="obs-wizard-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="obs-wizard-title"
      >
        <header className="obs-wizard-header">
          <div>
            <h2 id="obs-wizard-title">Observation vector setup</h2>
            <p className="obs-wizard-sub">
              Configure each observation term one by one. Running total:{" "}
              <span className="mono obs-wizard-total">{breakdown.totalDim}</span> dims
            </p>
          </div>
          <button type="button" className="header-btn" onClick={onDismiss} title="Use Observations tab instead">
            Dismiss
          </button>
        </header>

        {!onReview && current ? (
          <div className="obs-wizard-body">
            <p className="obs-wizard-progress">
              Step {step + 1} of {draft.length} · {CATEGORY_LABELS[(current.category || "sensor") as keyof typeof CATEGORY_LABELS] ?? current.category}
            </p>

            <article className={`obs-wizard-step ${!current.available ? "obs-unavailable" : ""}`}>
              <div className="obs-wizard-step-head">
                <h3>{current.label || current.key || current.id}</h3>
                <span className="obs-dim-badge mono obs-dim-badge-active">
                  {formatObservationTermDimLabel(termForDim(current), dimCtx)} dims
                </span>
              </div>
              <p className="obs-wizard-desc">
                {OBSERVATION_KIND_HINTS[current.kind] ??
                  OBSERVATION_CATEGORY_HINTS[current.category || "sensor"] ??
                  current.description ??
                  ""}
              </p>

              {!current.available ? (
                <p className="obs-wizard-unavail">Not exported for this project — skipped.</p>
              ) : (
                <>
                  <Checkbox
                    checked={current.enabled}
                    onChange={(v) => setIncluded(current, v)}
                    label="Include in policy observation vector"
                  />

                  {current.source === "sensor" && sensorAvailableFields(current).length > 0 && current.enabled ? (
                    <fieldset className="obs-wizard-fields">
                      <legend>Sensor fields (each adds dimensions)</legend>
                      <ul className="obs-field-list">
                        {sensorAvailableFields(current).map((field) => {
                          const fd = computeObservationFieldDim(current.kind, field);
                          const checked = (current.fields ?? []).includes(field);
                          return (
                            <li key={field}>
                              <label className="obs-field-row">
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={(e) => toggleField(current, field, e.target.checked)}
                                />
                                <span className="mono">{field}</span>
                                <span className="obs-field-dim">+{fd}</span>
                              </label>
                            </li>
                          );
                        })}
                      </ul>
                    </fieldset>
                  ) : null}

                  {current.source === "sensor" && current.topic ? (
                    <p className="obs-wizard-meta mono">Topic: {current.topic}</p>
                  ) : null}
                </>
              )}
            </article>
          </div>
        ) : (
          <div className="obs-wizard-body">
            <h3 className="obs-wizard-review-title">Review observation vector</h3>
            <p className="obs-wizard-sub">
              {breakdown.enabledTermCount} enabled terms · total{" "}
              <span className="mono">{breakdown.totalDim}</span> dimensions
            </p>
            <div className="obs-wizard-review-table-wrap">
              <table className="obs-vector-table obs-wizard-review-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Term</th>
                    <th>Included</th>
                    <th>Dims</th>
                    <th>Start</th>
                  </tr>
                </thead>
                <tbody>
                  {breakdown.segments.map((seg, i) => (
                    <tr key={seg.termId} className={seg.enabled && seg.available ? "" : "obs-review-muted"}>
                      <td>{i + 1}</td>
                      <td>{seg.label}</td>
                      <td>{seg.enabled && seg.available ? "yes" : "no"}</td>
                      <td className="mono">{seg.enabled && seg.available ? seg.dim : "—"}</td>
                      <td className="mono">{seg.startIndex ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={3}>
                      <strong>Total</strong>
                    </td>
                    <td className="mono">
                      <strong>{breakdown.totalDim}</strong>
                    </td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        <footer className="obs-wizard-footer">
          <button type="button" className="header-btn" disabled={step === 0} onClick={goBack}>
            Back
          </button>
          <div className="obs-wizard-footer-spacer" />
          {!onReview ? (
            <button type="button" className="header-btn primary" onClick={goNext}>
              {step + 1 >= draft.length ? "Review" : "Next"}
            </button>
          ) : (
            <button type="button" className="header-btn primary" onClick={() => onConfirm(draft.map(termForDim))}>
              Confirm observation vector
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}

export function shouldShowObservationWizard(model: {
  observationTerms?: ObservationTerm[];
  observationsSetupComplete?: boolean;
  observationWizardDismissed?: boolean;
} | null): boolean {
  if (!model) return false;
  if (model.observationsSetupComplete) return false;
  if (model.observationWizardDismissed) return false;
  return (model.observationTerms?.length ?? 0) > 0;
}

export function termDimWithFields(term: ObservationTerm, nJoints: number): number {
  return computeObservationTermDim(termForDim(term), { nJoints });
}
