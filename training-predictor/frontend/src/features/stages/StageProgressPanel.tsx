import { SectionCard } from "../../components/SectionCard";
import { useStudyStore } from "../../stores/studyStore";

/** Per-stage progress for sequential mode: one row per tuned stage, active stage highlighted. */
export function StageProgressPanel() {
  const status = useStudyStore((s) => s.status);
  const trialsPerStage = useStudyStore((s) => s.form.trials_per_stage);
  if (!status || status.mode !== "sequential_stage" || !status.stages?.length) return null;

  const current = status.current_stage_index;

  return (
    <SectionCard
      title="Stages"
      meta={`${status.stages.filter((s) => s.status === "done").length}/${status.stages.length} done`}
    >
      <div className="tp-stagelist">
        {status.stages.map((s) => {
          const total = s.status === "done" ? s.n_completed || trialsPerStage : trialsPerStage;
          const pct = total > 0 ? Math.min(100, Math.round((s.n_completed / total) * 100)) : 0;
          return (
            <div
              key={s.stage_index}
              className={`tp-stagerow ${s.stage_index === current ? "tp-stage-active" : ""}`}
            >
              <span className="tp-stage-name">
                <span className="tp-stage-idx">{s.stage_index + 1}</span>
                {s.stage_name}
                <span className="tp-stage-id">{s.stage_id}</span>
              </span>
              <span className={`tp-state tp-state-${s.status}`}>{s.status}</span>
              <span className="tp-stage-prog">
                <span className="tp-stage-bar">
                  <span style={{ width: `${pct}%` }} />
                </span>
                <span className="tp-stage-count">
                  {s.n_completed}/{total}
                </span>
              </span>
              <span className="tp-stage-best">
                {s.best_value !== null ? s.best_value : "—"}
              </span>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}
