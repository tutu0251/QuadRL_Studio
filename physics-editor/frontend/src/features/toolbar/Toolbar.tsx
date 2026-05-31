import { useState } from "react";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

type ValidationIssue = {
  code: string;
  message: string;
};

type ExportValidationResult = {
  valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  details?: { status?: string; durationS?: number; modelFile?: string };
};

async function pollTask(taskId: string) {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const t = await api.getTask(taskId);
    if (t.status === "completed" || t.status === "failed") return t;
  }
  return null;
}

function logValidationResult(
  log: (msg: string) => void,
  label: string,
  v: ExportValidationResult
) {
  const status = v.details?.status;
  if (status === "skipped") {
    const skipMsg = v.warnings.find((w) => w.code.includes("skipped"))?.message;
    log(skipMsg ?? `${label} skipped (not installed)`);
    return;
  }
  if (v.valid) {
    log(`${label} passed${v.warnings.length ? ` — ${v.warnings.length} warning(s)` : ""}`);
  } else {
    log(`${label} failed — ${v.errors.length} error(s)`);
    v.errors.forEach((e) => log(`  [${e.code}] ${e.message}`));
  }
  v.warnings.slice(0, 5).forEach((w) => log(`  ⚠ ${w.message}`));
  if (v.details?.durationS != null) {
    log(`  duration: ${v.details.durationS}s`);
  }
  if (v.details?.modelFile) {
    log(`  file: ${v.details.modelFile}`);
  }
}

export function Toolbar() {
  const project = useEditorStore((s) => s.project);
  const log = useEditorStore((s) => s.log);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    if (!project) return;
    const m = await api.getModel(project);
    useEditorStore.getState().setModel(m);
    const com = await api.robotCom(project);
    useEditorStore.getState().setWholeCom(com.com);
  };

  const runExport = async (fn: () => Promise<{ task_id: string }>, label: string) => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      if (!v.valid) {
        log(`Validation failed (${v.errors.length} errors)`);
        v.errors.slice(0, 3).forEach((e) => log(`  · ${e.message}`));
        return;
      }
      if (v.warnings.length) log(`${v.warnings.length} warning(s) — export allowed`);
      const { task_id } = await fn();
      log(`${label}…`);
      const t = await pollTask(task_id);
      if (t?.status === "completed") {
        log(`${label} complete`);
        const validation = t.result?.exportValidation;
        if (validation) {
          logValidationResult(log, "Export validation", validation);
        }
        await refresh();
      } else if (t?.status === "failed") {
        log(`${label} failed`);
        const validation = t.result?.exportValidation;
        if (validation) {
          logValidationResult(log, "Export validation", validation);
        }
      } else {
        log(`${label} timed out — see console for progress`);
      }
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <span className="toolbar-label">Check</span>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy}
          onClick={async () => {
            if (!project) return;
            const v = await api.validate(project);
            if (v.valid) log(`Valid — ${v.warnings.length} warning(s)`);
            else {
              log(`Invalid — ${v.errors.length} error(s)`);
              v.errors.forEach((e) => log(`  [${e.code}] ${e.message}`));
            }
            v.warnings.slice(0, 5).forEach((w) => log(`  ⚠ ${w.message}`));
          }}
        >
          Validate
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <span className="toolbar-label">Export</span>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy}
          onClick={() => void runExport(() => api.exportUrdf(project!), "URDF")}
        >
          phy URDF
        </button>
        <button
          type="button"
          className="toolbar-btn primary"
          disabled={!project || busy}
          onClick={() => void runExport(() => api.exportGazebo(project!), "SDF")}
        >
          phy SDF
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <span className="toolbar-label">Sim</span>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy}
          onClick={async () => {
            if (!project) return;
            const p = await api.gazeboPreview(project);
            if (p.exists) {
              log(`Spawn: ${p.command}`);
              await navigator.clipboard.writeText(p.command).catch(() => {});
              log("Command copied to clipboard");
            } else {
              log(`Export SDF first → ${p.sdf}`);
            }
          }}
        >
          Gazebo cmd
        </button>
      </div>

      {busy && <span className="toolbar-busy">Working…</span>}
    </div>
  );
}
