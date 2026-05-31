import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";

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

/** Wait for task completion. Logs stream via WebSocket (/ws/logs) in App.tsx. */
async function pollTask(taskId: string) {
  for (let i = 0; i < 120; i++) {
    const t = await api.getTask(taskId);
    if (t.status === "completed" || t.status === "failed") return t;
    await new Promise((r) => setTimeout(r, 500));
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
  const showLinkFrames = useEditorStore((s) => s.showLinkFrames);
  const showJointFrames = useEditorStore((s) => s.showJointFrames);
  const showJointAxes = useEditorStore((s) => s.showJointAxes);
  const toggleLinkFrames = useEditorStore((s) => s.toggleLinkFrames);
  const toggleJointFrames = useEditorStore((s) => s.toggleJointFrames);
  const toggleJointAxes = useEditorStore((s) => s.toggleJointAxes);

  const run = async (label: string, fn: () => Promise<{ task_id: string }>) => {
    if (!project) return;
    try {
      const { task_id } = await fn();
      log(`${label}…`);
      const t = await pollTask(task_id);
      if (t?.status === "completed") {
        log(`${label} complete`);
        const validation = (t.result as { exportValidation?: ExportValidationResult } | undefined)
          ?.exportValidation;
        if (validation) {
          logValidationResult(log, "Export validation", validation);
        }
      } else if (t?.status === "failed") {
        log(`${label} failed`);
        const validation = (t.result as { exportValidation?: ExportValidationResult } | undefined)
          ?.exportValidation;
        if (validation) {
          logValidationResult(log, "Export validation", validation);
        } else if (t.result && typeof t.result === "object" && "error" in t.result) {
          log(String((t.result as { error: unknown }).error));
        }
      } else {
        log(`${label} timed out — see console for progress`);
      }
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <header className="toolbar">
      <div className="btn-row">
        <button type="button" className={showLinkFrames ? "active" : ""} onClick={toggleLinkFrames}>
          Link Frames
        </button>
        <button type="button" className={showJointFrames ? "active" : ""} onClick={toggleJointFrames}>
          Joint Frames
        </button>
        <button type="button" className={showJointAxes ? "active" : ""} onClick={toggleJointAxes}>
          Joint Axes
        </button>
      </div>
      <div className="btn-row">
        <button type="button" disabled={!project} onClick={() => run("validate", () => api.validate(project!))}>
          Validate
        </button>
        <button type="button" disabled={!project} onClick={() => run("urdf export", () => api.exportUrdf(project!))}>
          Export URDF
        </button>
        <button type="button" disabled={!project} onClick={() => run("sdf export", () => api.exportSdf(project!))}>
          Export SDF
        </button>
        <button type="button" disabled={!project} onClick={() => run("export", () => api.exportBoth(project!))}>
          Export Both
        </button>
        <button
          type="button"
          disabled={!project}
          onClick={async () => {
            if (!project) return;
            const r = await api.createSnapshot(project);
            log(`Snapshot: ${r.snapshot_id}`);
          }}
        >
          Snapshot
        </button>
      </div>
    </header>
  );
}
