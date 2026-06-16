import { SectionCard } from "../../components/SectionCard";
import { describeParam } from "../../labels";
import { useStudyStore } from "../../stores/studyStore";

/** "Best so far": the leading trial's predicted parameters + a button to save them. */
export function BestPanel({ onApply }: { onApply: () => void }) {
  const status = useStudyStore((s) => s.status);
  const applyResult = useStudyStore((s) => s.applyResult);
  const applying = useStudyStore((s) => s.applying);
  const previewing = useStudyStore((s) => s.previewRef !== null);
  const best = status?.best ?? null;

  // Sequential mode has per-stage bests rather than a single trial. When there is no single
  // `best` to show (a loaded sequence, or between stages), surface the per-stage winners and
  // still allow "Save to project".
  const isSeq = status?.mode === "sequential_stage";
  const seqStages = isSeq ? status?.stages ?? [] : [];
  const seqApplyable = seqStages.some(
    (s) => s.status === "done" && s.best_params && Object.keys(s.best_params).length > 0
  );
  const canSave = (!!best || seqApplyable) && !applying;

  const total = status?.n_trials ?? 0;
  const done = status?.n_completed ?? 0;
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;

  return (
    <SectionCard
      title="Best so far"
      meta={best ? `trial #${best.number}` : previewing ? "loaded" : undefined}
      actions={
        <button
          type="button"
          className="tp-btn tp-btn-primary tp-btn-sm"
          disabled={!canSave}
          title="Write these parameters into the project's PPO / RL config files (originals are backed up)"
          onClick={onApply}
        >
          {applying ? "Saving…" : "Save to project"}
        </button>
      }
    >
      {status && !previewing ? (
        <div className="tp-progress">
          <div className="tp-progress-bar">
            <span style={{ width: `${pct}%` }} />
          </div>
          <span className="tp-progress-label">
            {done} / {total} trials{status.mock_objective ? " · practice run" : ""}
          </span>
        </div>
      ) : null}

      {best ? (
        <>
          <div className="tp-objective">
            <span className="tp-objective-value">{best.value}</span>
            <span className="tp-objective-label">objective (higher is better)</span>
          </div>
          <div className="tp-kv-list">
            {Object.entries(best.params).map(([key, value]) => {
              const meta = describeParam(key);
              return (
                <div className="tp-kv" key={key} title={meta.hint}>
                  <span className="tp-kv-key">
                    {meta.label}
                    <span className="tp-kv-code">{meta.code}</span>
                  </span>
                  <span className="tp-kv-val">{value}</span>
                </div>
              );
            })}
          </div>
        </>
      ) : isSeq && seqStages.length ? (
        <div className="tp-kv-list">
          {seqStages.map((s) => {
            const params = Object.entries(s.best_params ?? {});
            return (
              <div key={s.stage_index}>
                <div className="tp-kv">
                  <span className="tp-kv-key">
                    {s.stage_name}
                    <span className="tp-kv-code">{s.stage_id}</span>
                  </span>
                  <span className="tp-kv-val">
                    {s.status === "done" ? `best ${s.best_value ?? "—"}` : s.status}
                  </span>
                </div>
                {params.map(([key, value]) => {
                  const meta = describeParam(key);
                  return (
                    <div className="tp-kv" key={`${s.stage_index}-${key}`} title={meta.hint}>
                      <span className="tp-kv-key">
                        {meta.label}
                        <span className="tp-kv-code">{meta.code}</span>
                      </span>
                      <span className="tp-kv-val">{value}</span>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="tp-empty">No completed trials yet — the best parameters will appear here.</p>
      )}

      {applyResult ? <div className="tp-apply-result">{applyResult}</div> : null}
    </SectionCard>
  );
}
