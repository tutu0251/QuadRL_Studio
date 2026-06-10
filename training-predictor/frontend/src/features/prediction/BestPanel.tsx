import { SectionCard } from "../../components/SectionCard";
import { describeParam } from "../../labels";
import { useStudyStore } from "../../stores/studyStore";

/** "Best so far": the leading trial's predicted parameters + a button to save them. */
export function BestPanel({ onApply }: { onApply: () => void }) {
  const status = useStudyStore((s) => s.status);
  const applyResult = useStudyStore((s) => s.applyResult);
  const applying = useStudyStore((s) => s.applying);
  const best = status?.best ?? null;

  const total = status?.n_trials ?? 0;
  const done = status?.n_completed ?? 0;
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;

  return (
    <SectionCard
      title="Best so far"
      meta={best ? `trial #${best.number}` : undefined}
      actions={
        <button
          type="button"
          className="tp-btn tp-btn-primary tp-btn-sm"
          disabled={!best || applying}
          title="Write these parameters into the project's PPO / RL config files (originals are backed up)"
          onClick={onApply}
        >
          {applying ? "Saving…" : "Save to project"}
        </button>
      }
    >
      {status ? (
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
      ) : (
        <p className="tp-empty">No completed trials yet — the best parameters will appear here.</p>
      )}

      {applyResult ? <div className="tp-apply-result">{applyResult}</div> : null}
    </SectionCard>
  );
}
