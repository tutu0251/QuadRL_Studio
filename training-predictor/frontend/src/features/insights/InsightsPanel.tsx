import { SectionCard } from "../../components/SectionCard";
import type { SearchSpec } from "../../api/types";
import { describeParam } from "../../labels";
import { useStudyStore } from "../../stores/studyStore";

/** Render a spec bound as a compact range / fixed value. */
function fmtBound(b: Partial<SearchSpec>): string {
  if (!b) return "";
  if (b.fixed !== null && b.fixed !== undefined) return `fixed ${b.fixed}`;
  return `${b.low ?? "?"} … ${b.high ?? "?"}`;
}

/** Claude's coaching log: what it changed after each review, and why. */
export function InsightsPanel() {
  const decisions = useStudyStore((s) => s.status?.decisions ?? []);

  return (
    <SectionCard title="Claude's insights" meta={decisions.length ? `${decisions.length}` : undefined}>
      {decisions.length === 0 ? (
        <p className="tp-empty">
          Claude reviews progress every few trials. Its decisions — re-centered ranges, reward
          rebalancing, or an early stop — will show up here.
        </p>
      ) : (
        <div className="tp-scroll tp-insights">
          {decisions
            .slice()
            .reverse()
            .map((d, i) => (
              <article className="tp-decision" key={`${d.after_trial}-${i}`}>
                <header>
                  <span className="tp-decision-action">{d.action}</span>
                  {d.stop ? <span className="tp-tag tp-tag-stop">stop</span> : null}
                  <span className="tp-decision-meta">after {d.after_trial} trials</span>
                </header>
                {d.rationale ? <p className="tp-decision-why">{d.rationale}</p> : null}
                {d.changes?.length ? (
                  <ul className="tp-decision-changes">
                    {d.changes.map((c, j) => {
                      const meta = describeParam(c.name);
                      return (
                        <li key={j} title={meta.hint}>
                          <span className="tp-change-name">{meta.label}</span>
                          <span className="tp-change-range">
                            {fmtBound(c.before)} → {fmtBound(c.after)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </article>
            ))}
        </div>
      )}
    </SectionCard>
  );
}
