import { useState } from "react";
import { api } from "../../api/client";
import { usePlannerStore } from "../../stores/plannerStore";

async function pollTask(taskId: string) {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const t = await api.getTask(taskId);
    if (t.status === "completed" || t.status === "failed") return t;
  }
  return null;
}

export function Toolbar() {
  const project = usePlannerStore((s) => s.project);
  const model = usePlannerStore((s) => s.model);
  const setModel = usePlannerStore((s) => s.setModel);
  const setValidation = usePlannerStore((s) => s.setValidation);
  const validation = usePlannerStore((s) => s.validation);
  const log = usePlannerStore((s) => s.log);
  const [busy, setBusy] = useState(false);

  const recommend = async () => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const r = await api.recommend(project);
      const m = await api.getModel(project);
      setModel(m);
      r.notes.forEach((n) => log(n));
      log("Recommendations applied");
      const v = await api.validate(project);
      setValidation(v);
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      setValidation(v);
      if (v.valid) log(`Validation OK (${v.warnings.length} warnings)`);
      else log(`Validation failed: ${v.errors.length} errors`);
      v.errors.slice(0, 5).forEach((e) => log(`  · ${e.message}`));
      v.warnings.slice(0, 3).forEach((w) => log(`  ⚠ ${w.message}`));
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const exportPpo = async () => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      setValidation(v);
      if (!v.valid) {
        log(`Validation failed (${v.errors.length} errors)`);
        return;
      }
      const { task_id } = await api.exportPpo(project);
      log("Exporting ppo_<project>_config.yaml…");
      const t = await pollTask(task_id);
      if (t?.status === "completed") log(`Export complete: ${t.result?.ppo_config ?? ""}`);
      else log("Export failed");
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <span className="toolbar-label">Tune</span>
        <button
          type="button"
          className="toolbar-btn primary"
          disabled={!project || busy}
          onClick={() => void recommend()}
        >
          <span className="btn-icon" aria-hidden>
            ◈
          </span>
          Recommend
        </button>
      </div>

      <span className="toolbar-divider" />

      <div className="toolbar-group">
        <span className="toolbar-label">Check</span>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy}
          onClick={() => void validate()}
        >
          Validate
        </button>
        {validation && (
          <span className={`toolbar-chip ${validation.valid ? "ok" : "err"}`}>
            {validation.valid ? "OK" : `${validation.errors.length} err`}
          </span>
        )}
      </div>

      <span className="toolbar-divider" />

      <div className="toolbar-group">
        <span className="toolbar-label">Output</span>
        <button
          type="button"
          className="toolbar-btn accent"
          disabled={!project || busy}
          onClick={() => void exportPpo()}
        >
          Export YAML
        </button>
      </div>

      <span className="toolbar-spacer" />

      {busy && <span className="toolbar-busy">Working…</span>}
      {model && project && (
        <span className="toolbar-context mono">
          {model.params.device} · {model.params.numEnvs} env
          {model.params.numEnvs > 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}
