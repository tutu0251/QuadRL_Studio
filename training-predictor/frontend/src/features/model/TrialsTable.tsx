import { SectionCard } from "../../components/SectionCard";
import { describeParam } from "../../labels";
import { useStudyStore } from "../../stores/studyStore";

/** Compact, friendly rendering of a trial's sampled parameters. */
function ParamChips({ params }: { params: Record<string, number | string> }) {
  const entries = Object.entries(params);
  if (entries.length === 0) return <span className="tp-muted">—</span>;
  return (
    <span className="tp-chips">
      {entries.map(([key, value]) => {
        const meta = describeParam(key);
        return (
          <span className="tp-paramchip" key={key} title={`${meta.code} — ${meta.hint ?? ""}`}>
            <span className="tp-paramchip-name">{meta.label}</span>
            <span className="tp-paramchip-val">{value}</span>
          </span>
        );
      })}
    </span>
  );
}

/** Every trial the optimizer has run, newest first. */
export function TrialsTable() {
  const trials = useStudyStore((s) => s.trials);
  const best = useStudyStore((s) => s.status?.best ?? null);

  return (
    <SectionCard title="Trials" meta={trials.length ? `${trials.length}` : undefined}>
      {trials.length === 0 ? (
        <p className="tp-empty">Trials will stream in here as the study runs.</p>
      ) : (
        <div className="tp-scroll tp-table-wrap">
          <table className="tp-table">
            <thead>
              <tr>
                <th className="tp-col-num">Trial</th>
                <th className="tp-col-state">State</th>
                <th className="tp-col-obj">Objective</th>
                <th>Parameters</th>
              </tr>
            </thead>
            <tbody>
              {trials
                .slice()
                .reverse()
                .map((t) => (
                  <tr key={t.number} className={best && best.number === t.number ? "tp-row-best" : ""}>
                    <td className="tp-col-num">
                      #{t.number}
                      {best && best.number === t.number ? <span className="tp-tag tp-tag-best">best</span> : null}
                    </td>
                    <td className="tp-col-state">
                      <span className={`tp-state tp-state-${t.state.toLowerCase()}`}>{t.state}</span>
                    </td>
                    <td className="tp-col-obj">{t.value ?? "—"}</td>
                    <td>
                      <ParamChips params={t.params} />
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
}
