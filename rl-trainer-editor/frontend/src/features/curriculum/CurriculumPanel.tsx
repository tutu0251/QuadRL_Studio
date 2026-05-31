import { useEffect, useState } from "react";
import { CURRICULUM_CATALOG, type CurriculumInfo, type CurriculumStage } from "@rl-trainer-model";
import { api } from "../../api/client";
import { StageInspector } from "../stage/StageInspector";
import { formatStageGaitTypes } from "../stage/stageGaitUtils";
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
  const setSelectedStageId = useTrainerStore((s) => s.setSelectedStageId);
  const selectedStageId = useTrainerStore((s) => s.selectedStageId);
  const log = useTrainerStore((s) => s.log);
  const [catalog, setCatalog] = useState<CurriculumInfo[]>(CURRICULUM_CATALOG);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    api.curricula().then((r) => setCatalog(r.curricula)).catch(() => {});
  }, []);

  const cur = model?.curriculum;
  const stageIdsKey = cur?.stages.map((s) => s.id).join("|") ?? "";

  useEffect(() => {
    if (!cur?.stages.length) return;
    const sorted = [...cur.stages].sort((a, b) => a.order - b.order);
    if (selectedStageId && sorted.some((s) => s.id === selectedStageId)) return;
    setSelectedStageId(sorted[0].id);
  }, [stageIdsKey, selectedStageId, setSelectedStageId, cur?.stages.length]);

  if (!model || !project || !cur) return null;

  const library = model.curriculumLibrary ?? [];
  const stages = [...cur.stages].sort((a, b) => a.order - b.order);
  const totalSteps = stages.reduce((s, st) => s + st.timesteps, 0);

  const applyCurriculum = async (id: string) => {
    try {
      const m = await api.applyCurriculum(project, id);
      setModel(m);
      const sorted = [...m.curriculum.stages].sort((a, b) => a.order - b.order);
      if (sorted[0]) setSelectedStageId(sorted[0].id);
      log(`Applied curriculum template: ${id}`);
    } catch (e) {
      log(String(e));
    }
  };

  const selectLibraryEntry = async (entryId: string) => {
    try {
      const m = await api.patchModel(project, { activeCurriculumId: entryId });
      setModel(m);
      const sorted = [...m.curriculum.stages].sort((a, b) => a.order - b.order);
      if (sorted[0]) setSelectedStageId(sorted[0].id);
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
      const m = await api.deleteStage(project, stageId);
      setModel(m);
      const sorted = [...m.curriculum.stages].sort((a, b) => a.order - b.order);
      if (selectedStageId === stageId) {
        setSelectedStageId(sorted[0]?.id ?? null);
      }
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

  const addStage = async () => {
    try {
      const m = await api.addStage(project);
      setModel(m);
      const sorted = [...m.curriculum.stages].sort((a, b) => a.order - b.order);
      const last = sorted[sorted.length - 1];
      if (last) setSelectedStageId(last.id);
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
      <div className="curriculum-layout editor-split-layout">
        <aside className="curriculum-library editor-sidebar">
          <div className="library-user-section">
            <div className="pane-header">
              <h4 className="pane-title">Curriculums</h4>
              <span className="pane-badge">{library.length}</span>
            </div>
            <div className="library-list">
              {library.length === 0 && (
                <p className="empty-desc sidebar-empty">Create one or pick a template below.</p>
              )}
              {library.map((entry) => (
                <div
                  key={entry.id}
                  className={`library-item ${model.activeCurriculumId === entry.id ? "selected" : ""}`}
                >
                  <button
                    type="button"
                    className="library-select"
                    onClick={() => void selectLibraryEntry(entry.id)}
                  >
                    <strong>{entry.name}</strong>
                    <span className="preset-meta">
                      {entry.stages.length} stages · {entry.terrainProfile}
                    </span>
                  </button>
                  <div className="library-actions">
                    <button
                      type="button"
                      className="icon-btn"
                      title="Duplicate"
                      onClick={() => void duplicateCurriculumEntry(entry.id)}
                    >
                      ⧉
                    </button>
                    <button
                      type="button"
                      className="icon-btn danger"
                      title="Delete"
                      onClick={() => void deleteCurriculumEntry(entry.id)}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="library-create">
              <input
                className="param-input"
                placeholder="New curriculum name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void createCurriculum()}
              />
              <button type="button" className="header-btn primary" onClick={() => void createCurriculum()}>
                + Create
              </button>
            </div>
          </div>

          <div className="library-templates-section sidebar-footer">
            <h4 className="section-label">Templates</h4>
            <div className="template-list">
              {catalog.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`template-card ${cur.curriculumId === c.id ? "selected" : ""}`}
                  onClick={() => void applyCurriculum(c.id)}
                >
                  <strong>{c.name}</strong>
                  <span className="preset-meta">{c.description}</span>
                  <span className="preset-meta mono">
                    {c.stageCount} stages · {formatSteps(c.totalTimesteps)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div className="curriculum-main editor-main-pane">
          {stages.length > 0 ? (
            <>
              <div className="editor-toolbar">
                <span className="editor-toolbar-title">{cur.name || "Untitled curriculum"}</span>
                <div className="editor-toolbar-chips">
                  <span className="editor-chip">{formatSteps(totalSteps)} steps</span>
                  <span className="editor-chip">{cur.terrainProfile}</span>
                  <span className="editor-chip">{stages.length} stages</span>
                </div>
                <button type="button" className="header-btn primary" onClick={() => void recommendAll()}>
                  Auto-recommend
                </button>
              </div>

              <div className="stage-workspace">
                <section className="stage-pipeline-pane editor-pane" aria-label="Training order">
                  <div className="pane-header pane-header-actions">
                    <h4 className="pane-title">Stages</h4>
                    <button type="button" className="header-btn" onClick={() => void addStage()}>
                      + Add stage
                    </button>
                  </div>
                  <ol className="curriculum-pipeline pipeline-scroll">
                    {stages.map((stage, i) => (
                      <li
                        key={stage.id}
                        className={`curriculum-stage pipeline-item stage-card ${selectedStageId === stage.id ? "selected" : ""}`}
                      >
                        <button type="button" className="stage-card-body" onClick={() => selectStage(stage)}>
                          <span className="stage-num">{i + 1}</span>
                          <span className="stage-card-text">
                            <strong>{stage.name}</strong>
                            <span className="mono stage-vel">
                              {formatStageGaitTypes(stage)} · {formatSteps(stage.timesteps)}
                            </span>
                          </span>
                        </button>
                        <div className="stage-actions stage-actions-hover">
                          <button type="button" className="icon-btn" title="Move up" disabled={i === 0} onClick={() => void reorderStage(stage.id, "up")}>↑</button>
                          <button type="button" className="icon-btn" title="Move down" disabled={i === stages.length - 1} onClick={() => void reorderStage(stage.id, "down")}>↓</button>
                          <button type="button" className="icon-btn" title="Duplicate" onClick={() => void duplicateStage(stage.id)}>⧉</button>
                          <button type="button" className="icon-btn danger" title="Delete" onClick={() => void deleteStage(stage.id)}>✕</button>
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>

                <section className="stage-inspector-pane editor-pane" aria-label="Stage parameters">
                  <div className="pane-header">
                    <h4 className="pane-title">Stage inspector</h4>
                  </div>
                  <StageInspector compact />
                </section>
              </div>
            </>
          ) : (
            <div className="editor-empty-state compact">
              <p className="empty-desc">Pick a template or create a curriculum and add stages to begin.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
