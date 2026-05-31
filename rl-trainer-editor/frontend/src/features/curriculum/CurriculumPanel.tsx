import { useEffect, useState } from "react";
import { CURRICULUM_CATALOG, type CurriculumInfo, type CurriculumStage } from "@rl-trainer-model";
import { api } from "../../api/client";
import { Toggle } from "../../components/Toggle";
import { useTrainerStore } from "../../stores/trainerStore";
import { CheckpointSelector } from "./CheckpointSelector";

function formatSteps(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

export function CurriculumPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const setActiveTab = useTrainerStore((s) => s.setActiveTab);
  const setSelectedStageId = useTrainerStore((s) => s.setSelectedStageId);
  const selectedStageId = useTrainerStore((s) => s.selectedStageId);
  const log = useTrainerStore((s) => s.log);
  const [catalog, setCatalog] = useState<CurriculumInfo[]>(CURRICULUM_CATALOG);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    api.curricula().then((r) => setCatalog(r.curricula)).catch(() => {});
  }, []);

  if (!model || !project) return null;

  const cur = model.curriculum;
  const library = model.curriculumLibrary ?? [];
  const stages = [...cur.stages].sort((a, b) => a.order - b.order);
  const totalSteps = stages.reduce((s, st) => s + st.timesteps, 0);
  const tc = model.trainingCheckpoint ?? { resumeCheckpointPath: null, checkpointDirectory: "checkpoints" };

  const patchCurriculum = async (body: Partial<typeof cur>) => {
    try {
      setModel(await api.patchModel(project, { curriculum: { ...cur, ...body } }));
    } catch (e) {
      log(String(e));
    }
  };

  const patchCheckpoint = async (patch: Partial<typeof tc>) => {
    try {
      setModel(
        await api.patchModel(project, {
          trainingCheckpoint: { ...tc, ...patch },
        })
      );
    } catch (e) {
      log(String(e));
    }
  };

  const applyCurriculum = async (id: string) => {
    try {
      const m = await api.applyCurriculum(project, id);
      setModel(m);
      log(`Applied curriculum template: ${id}`);
    } catch (e) {
      log(String(e));
    }
  };

  const selectLibraryEntry = async (entryId: string) => {
    try {
      setModel(await api.patchModel(project, { activeCurriculumId: entryId }));
    } catch (e) {
      log(String(e));
    }
  };

  const createCurriculum = async () => {
    try {
      setModel(await api.addCurriculum(project, { name: newName || "New curriculum" }));
      setNewName("");
      log("Created curriculum");
    } catch (e) {
      log(String(e));
    }
  };

  const deleteCurriculumEntry = async (entryId: string) => {
    try {
      setModel(await api.deleteCurriculum(project, entryId));
      log("Deleted curriculum");
    } catch (e) {
      log(String(e));
    }
  };

  const duplicateCurriculumEntry = async (entryId: string) => {
    try {
      setModel(await api.duplicateCurriculum(project, entryId));
      log("Duplicated curriculum");
    } catch (e) {
      log(String(e));
    }
  };

  const selectStage = (stage: CurriculumStage) => {
    setSelectedStageId(stage.id);
    setActiveTab("stage");
  };

  const duplicateStage = async (stageId: string) => {
    try {
      setModel(await api.duplicateStage(project, stageId));
      log("Duplicated stage");
    } catch (e) {
      log(String(e));
    }
  };

  const deleteStage = async (stageId: string) => {
    try {
      setModel(await api.deleteStage(project, stageId));
      if (selectedStageId === stageId) setSelectedStageId(null);
      log("Deleted stage");
    } catch (e) {
      log(String(e));
    }
  };

  const reorderStage = async (stageId: string, direction: "up" | "down") => {
    try {
      setModel(await api.reorderStage(project, stageId, direction));
    } catch (e) {
      log(String(e));
    }
  };

  const addStage = async (afterOrder?: number) => {
    try {
      setModel(await api.addStage(project, afterOrder));
      log("Added stage");
    } catch (e) {
      log(String(e));
    }
  };

  const recommendAll = async () => {
    try {
      setModel(await api.recommendCurriculum(project));
      log("Applied curriculum recommendations");
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <div className="tab-panel curriculum-panel">
      <div className="curriculum-layout">
        <aside className="curriculum-library">
          <h4 className="section-label">Curriculums</h4>
          {library.map((entry) => (
            <div
              key={entry.id}
              className={`library-item ${model.activeCurriculumId === entry.id ? "selected" : ""}`}
            >
              <button type="button" className="library-select" onClick={() => void selectLibraryEntry(entry.id)}>
                <strong>{entry.name}</strong>
                <span className="preset-meta">{entry.stages.length} stages · {entry.terrainProfile}</span>
              </button>
              <div className="library-actions">
                <button type="button" className="icon-btn" title="Duplicate" onClick={() => void duplicateCurriculumEntry(entry.id)}>⧉</button>
                <button type="button" className="icon-btn danger" title="Delete" onClick={() => void deleteCurriculumEntry(entry.id)}>✕</button>
              </div>
            </div>
          ))}
          <div className="library-create">
            <input
              className="param-input"
              placeholder="New curriculum name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <button type="button" className="header-btn" onClick={() => void createCurriculum()}>+ Create</button>
          </div>
        </aside>

        <div className="curriculum-main">
          <div className="curriculum-templates">
            <h4 className="section-label">Recommended templates</h4>
            <div className="template-grid">
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
          </div>

          <Toggle
            label="Enable progressive curriculum"
            checked={cur.enabled}
            onChange={(v) => void patchCurriculum({ enabled: v })}
          />
          <Toggle
            label="Load checkpoint from previous stage"
            hint="Fine-tune policy when advancing between stages"
            checked={cur.loadPreviousCheckpoint}
            onChange={(v) => void patchCurriculum({ loadPreviousCheckpoint: v })}
          />
          <Toggle
            label="Reset policy on stage advance"
            checked={cur.resetPolicyOnStageAdvance}
            onChange={(v) => void patchCurriculum({ resetPolicyOnStageAdvance: v })}
          />

          <CheckpointSelector project={project} config={tc} onChange={(p) => void patchCheckpoint(p)} />

          {cur.enabled && (
            <>
              <div className="curriculum-summary">
                <span>
                  Total: <strong className="mono">{formatSteps(totalSteps)}</strong> env steps
                </span>
                <span>
                  Terrain: <strong>{cur.terrainProfile}</strong>
                </span>
                <button type="button" className="header-btn" onClick={() => void recommendAll()}>
                  Auto-recommend all stages
                </button>
              </div>

              <div className="pipeline-header">
                <h4 className="section-label">Training order</h4>
                <button type="button" className="header-btn" onClick={() => void addStage()}>+ Add stage</button>
              </div>

              <ol className="curriculum-pipeline">
                {stages.map((stage, i) => (
                  <li
                    key={stage.id}
                    className={`curriculum-stage ${selectedStageId === stage.id ? "selected" : ""}`}
                  >
                    <div className="stage-header">
                      <span className="stage-num">{i + 1}</span>
                      <button type="button" className="stage-title-btn" onClick={() => selectStage(stage)}>
                        <strong>{stage.name}</strong>
                        <span className="mono stage-vel">
                          {stage.gaitTypeId} · v={stage.command?.targetLinVelX?.toFixed(2) ?? stage.targetLinVelX.toFixed(2)} m/s
                        </span>
                      </button>
                      <div className="stage-actions">
                        <button type="button" className="icon-btn" title="Move up" disabled={i === 0} onClick={() => void reorderStage(stage.id, "up")}>↑</button>
                        <button type="button" className="icon-btn" title="Move down" disabled={i === stages.length - 1} onClick={() => void reorderStage(stage.id, "down")}>↓</button>
                        <button type="button" className="icon-btn" title="Duplicate" onClick={() => void duplicateStage(stage.id)}>⧉</button>
                        <button type="button" className="icon-btn danger" title="Delete" onClick={() => void deleteStage(stage.id)}>✕</button>
                      </div>
                    </div>
                    <p className="stage-desc">{stage.description || `${formatSteps(stage.timesteps)} steps`}</p>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
