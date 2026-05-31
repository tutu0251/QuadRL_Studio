import { useState } from "react";
import { api } from "../../api/client";
import { useTrainerStore } from "../../stores/trainerStore";

async function pollTask(taskId: string, max = 7200) {
  for (let i = 0; i < max; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const t = await api.getTask(taskId);
    if (t.status === "completed" || t.status === "failed" || t.status === "cancelled") {
      return t;
    }
  }
  return null;
}

export function Toolbar() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const setValidation = useTrainerStore((s) => s.setValidation);
  const validation = useTrainerStore((s) => s.validation);
  const log = useTrainerStore((s) => s.log);
  const [busy, setBusy] = useState(false);

  const refreshProfile = async () => {
    if (!project || busy) return;
    setBusy(true);
    try {
      setModel(await api.refreshMachineProfile(project));
      log("Machine profile refreshed");
      setValidation(await api.validate(project));
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
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const exportRl = async () => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      setValidation(v);
      if (!v.valid) {
        log(`Validation failed (${v.errors.length} errors)`);
        return;
      }
      const { task_id } = await api.exportRl(project);
      log("Exporting rl_<project>_config.yaml…");
      const t = await pollTask(task_id, 120);
      if (t?.status === "completed") log(`Export complete: ${t.result?.rl_config ?? ""}`);
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
        <span className="toolbar-label">Host</span>
        <button
          type="button"
          className="toolbar-btn primary"
          disabled={!project || busy}
          onClick={() => void refreshProfile()}
        >
          Profile machine
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
        <button
          type="button"
          className="toolbar-btn accent"
          disabled={!project || busy}
          onClick={() => void exportRl()}
        >
          Export YAML
        </button>
      </div>

      <span className="toolbar-spacer" />
      {busy && <span className="toolbar-busy">Working…</span>}
      {model && project && (
        <span className="toolbar-context mono">
          {enabledTerms(model)} rewards
          {model.curriculum.enabled ? " · curriculum" : ""}
        </span>
      )}
    </div>
  );
}

function enabledTerms(model: { rewardTerms: { enabled: boolean }[] }): number {
  return model.rewardTerms.filter((t) => t.enabled).length;
}
