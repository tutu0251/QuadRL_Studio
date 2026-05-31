import { useState } from "react";
import { api, wsLogsUrl } from "../../api/client";
import { PROFILE_IMPLEMENTED, type TrainingProfile, type ValidationResult } from "@control-model";
import { useEditorStore } from "../../stores/editorStore";

/** Control runtime validation (Gazebo + joint probe) often exceeds 2 minutes. */
const POLL_INTERVAL_MS = 500;
const POLL_TIMEOUT_MS = 20 * 60 * 1000;

type TaskStatus = Awaited<ReturnType<typeof api.getTask>>;

function waitForTask(taskId: string): Promise<TaskStatus | null> {
  return new Promise((resolve) => {
    let settled = false;
    let ws: WebSocket | null = null;

    const finish = (task: TaskStatus | null) => {
      if (settled) return;
      settled = true;
      window.clearInterval(pollTimer);
      ws?.close();
      resolve(task);
    };

    const pollTimer = window.setInterval(async () => {
      try {
        const t = await api.getTask(taskId);
        if (t.status === "completed" || t.status === "failed") {
          finish(t);
        }
      } catch {
        /* keep polling */
      }
    }, POLL_INTERVAL_MS);

    window.setTimeout(() => {
      void api.getTask(taskId).then(finish).catch(() => finish(null));
    }, POLL_TIMEOUT_MS);

    try {
      ws = new WebSocket(wsLogsUrl());
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data) as {
          type?: string;
          task_id?: string;
          status?: string;
        };
        if (data.type === "status" && data.task_id === taskId) {
          if (data.status === "completed" || data.status === "failed") {
            void api.getTask(taskId).then(finish).catch(() => finish(null));
          }
        }
      };
    } catch {
      /* polling-only fallback */
    }
  });
}

function logValidationResult(
  log: (msg: string) => void,
  label: string,
  v: ValidationResult,
  focusConsole?: () => void
) {
  const status = v.details?.status as string | undefined;
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
    focusConsole?.();
  }
  v.warnings.slice(0, 5).forEach((w) => log(`  ⚠ ${w.message}`));
  if (v.details && typeof v.details.expectedJointCount === "number") {
    log(
      `  joints: model=${v.details.expectedJointCount} urdf=${v.details.urdfJointCount ?? "?"} ` +
        `controllers=${v.details.controllerJointCount ?? "?"} gains=${v.details.gainsJointCount ?? "?"}`
    );
  }
  const probe = v.details?.control_probe as
    | { joint?: string; moved?: boolean; action_ok?: boolean }
    | undefined;
  if (probe?.joint) {
    log(`  control probe: ${probe.joint} moved=${probe.moved ?? "?"} action=${probe.action_ok ?? "?"}`);
  }
  if (v.details?.durationS != null) {
    log(`  duration: ${v.details.durationS}s`);
  }
}

const PROFILES: TrainingProfile[] = ["ProfileA", "ProfileB", "ProfileC"];

export function Toolbar() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);
  const focusConsole = useEditorStore((s) => s.focusConsole);
  const [busy, setBusy] = useState(false);

  const profile = model?.trainingProfile ?? "ProfileA";

  const onProfileChange = async (p: TrainingProfile) => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const m = await api.setProfile(project, p);
      setModel(m);
      log(`Profile → ${p}`);
      if (!PROFILE_IMPLEMENTED[p]) {
        log(`${p} is not implemented — export disabled`);
      }
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const runExport = async () => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      if (!v.valid) {
        log(`Model validation failed (${v.errors.length} errors)`);
        v.errors.slice(0, 5).forEach((e) => log(`  · ${e.message}`));
        focusConsole();
        return;
      }
      v.warnings.slice(0, 3).forEach((w) => log(`  ⚠ ${w.message}`));
      const { task_id } = await api.exportRos2Control(project);
      log("Exporting ros2_control…");
      const t = await waitForTask(task_id);
      if (t?.status === "completed") {
        log("Export complete");
        if (t.result?.exportValidation) {
          logValidationResult(log, "Export validation", t.result.exportValidation);
        }
      } else if (t?.status === "failed") {
        log("Export failed");
        if (t.result?.exportValidation) {
          logValidationResult(log, "Export validation", t.result.exportValidation, focusConsole);
        } else if (t.result && "error" in t.result) {
          log(String(t.result.error));
          focusConsole();
        } else {
          focusConsole();
        }
      } else {
        log("Export timed out waiting for backend — see console for progress");
        focusConsole();
      }
    } catch (e) {
      log(String(e));
      focusConsole();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <span className="toolbar-label">Profile</span>
        <select
          className="toolbar-select"
          value={profile}
          disabled={!project || busy}
          onChange={(e) => void onProfileChange(e.target.value as TrainingProfile)}
        >
          {PROFILES.map((p) => (
            <option key={p} value={p}>
              {p}
              {!PROFILE_IMPLEMENTED[p] ? " (placeholder)" : ""}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy || profile !== "ProfileA"}
          title="Re-run auto-generation"
          onClick={async () => {
            if (!project) return;
            try {
              const m = await api.regenerate(project);
              setModel(m);
              log("Regenerated ProfileA gains");
            } catch (e) {
              log(String(e));
            }
          }}
        >
          Regenerate
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <span className="toolbar-label">Check</span>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy}
          onClick={async () => {
            if (!project) return;
            setBusy(true);
            try {
              const v = await api.validate(project);
              logValidationResult(log, "Model validation", v, v.valid ? undefined : focusConsole);
              try {
                const { task_id } = await api.validateExport(project);
                log("Running export validation…");
                const t = await waitForTask(task_id);
                if (t?.result?.exportValidation) {
                  logValidationResult(
                    log,
                    "Export validation",
                    t.result.exportValidation,
                    t.result.exportValidation.valid ? undefined : focusConsole
                  );
                } else if (t?.status === "failed" && t.result && "error" in t.result) {
                  log(String(t.result.error));
                  focusConsole();
                } else if (!t) {
                  log("Export validation timed out — see console for progress");
                  focusConsole();
                }
              } catch {
                /* export files optional */
              }
            } finally {
              setBusy(false);
            }
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
          className="toolbar-btn primary"
          disabled={!project || busy || profile !== "ProfileA"}
          onClick={() => void runExport()}
        >
          ros2_control
        </button>
      </div>

      {busy && <span className="toolbar-busy">Working…</span>}
    </div>
  );
}
