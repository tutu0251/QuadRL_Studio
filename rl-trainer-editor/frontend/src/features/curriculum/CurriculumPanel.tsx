import { useEffect, useState } from "react";
import { CURRICULUM_CATALOG, type CurriculumInfo, type CurriculumStage } from "@rl-trainer-model";
import { api } from "../../api/client";
import { NumberField } from "../../components/NumberField";
import { Toggle } from "../../components/Toggle";
import { useTrainerStore } from "../../stores/trainerStore";

function formatSteps(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

export function CurriculumPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const [catalog, setCatalog] = useState<CurriculumInfo[]>(CURRICULUM_CATALOG);

  useEffect(() => {
    api.curricula().then((r) => setCatalog(r.curricula)).catch(() => {});
  }, []);

  if (!model) return null;

  const cur = model.curriculum;
  const stages = [...cur.stages].sort((a, b) => a.order - b.order);
  const totalSteps = stages.reduce((s, st) => s + st.timesteps, 0);

  const patchCurriculum = async (body: Partial<typeof cur>) => {
    if (!project) return;
    try {
      setModel(await api.patchModel(project, { curriculum: { ...cur, ...body } }));
    } catch (e) {
      log(String(e));
    }
  };

  const applyCurriculum = async (id: string) => {
    if (!project) return;
    try {
      const m = await api.applyCurriculum(project, id);
      setModel(m);
      log(`Applied progressive curriculum: ${id}`);
    } catch (e) {
      log(String(e));
    }
  };

  const previewStage = async (index: number) => {
    if (!project) return;
    try {
      setModel(await api.setCurriculumStage(project, index));
      log(`Preview stage ${index + 1}: ${stages[index]?.name ?? ""}`);
    } catch (e) {
      log(String(e));
    }
  };

  const updateStage = async (index: number, patch: Partial<CurriculumStage>) => {
    if (!project) return;
    const next = stages.map((s, i) => (i === index ? { ...s, ...patch } : s));
    await patchCurriculum({ stages: next });
  };

  return (
    <div className="tab-panel curriculum-panel">
      <p className="panel-hint">
        Train step-by-step: stand still → walk → run → sprint. Each stage has its own rewards,
        velocity command, and timestep budget before advancing.
      </p>

      <div className="curriculum-templates">
        <h4 className="section-label">Recommended curricula</h4>
        {catalog.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`preset-card ${cur.curriculumId === c.id ? "selected" : ""}`}
            onClick={() => void applyCurriculum(c.id)}
          >
            <strong>{c.name}</strong>
            <p>{c.description}</p>
            <span className="preset-meta mono">
              {c.stageCount} stages · {formatSteps(c.totalTimesteps)} steps
            </span>
          </button>
        ))}
      </div>

      <Toggle
        label="Enable progressive curriculum"
        checked={cur.enabled}
        onChange={(v) => void patchCurriculum({ enabled: v })}
      />
      <Toggle
        label="Load checkpoint from previous stage"
        hint="Fine-tune policy when advancing instead of training from scratch"
        checked={cur.loadPreviousCheckpoint}
        onChange={(v) => void patchCurriculum({ loadPreviousCheckpoint: v })}
      />

      {cur.enabled && stages.length > 0 && (
        <>
          <div className="curriculum-summary">
            <span>
              Total: <strong className="mono">{formatSteps(totalSteps)}</strong> env steps
            </span>
            <span>
              Active stage: <strong>{cur.currentStageIndex + 1}</strong> / {stages.length}
            </span>
          </div>

          <ol className="curriculum-pipeline">
            {stages.map((stage, i) => (
              <li
                key={stage.id}
                className={`curriculum-stage ${
                  i === cur.currentStageIndex ? "current" : i < cur.currentStageIndex ? "done" : ""
                }`}
              >
                <div className="stage-header">
                  <span className="stage-num">{i + 1}</span>
                  <div className="stage-title">
                    <strong>{stage.name}</strong>
                    <span className="mono stage-vel">
                      v={stage.targetLinVelX.toFixed(2)} m/s
                    </span>
                  </div>
                  <button type="button" className="header-btn" onClick={() => void previewStage(i)}>
                    Preview
                  </button>
                </div>
                <p className="stage-desc">{stage.description}</p>
                <div className="stage-fields">
                  <NumberField
                    label="timesteps"
                    value={stage.timesteps}
                    step={10_000}
                    onChange={(v) => void updateStage(i, { timesteps: Math.max(10_000, Math.round(v)) })}
                  />
                  <NumberField
                    label="target_lin_vel_x"
                    value={stage.targetLinVelX}
                    step={0.1}
                    onChange={(v) => void updateStage(i, { targetLinVelX: v })}
                  />
                </div>
                <p className="stage-advance mono">
                  Advance when reward ≥ {stage.advanceCriteria.minMeanEpisodeReward}, fall rate ≤{" "}
                  {stage.advanceCriteria.maxFallRate}
                </p>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
