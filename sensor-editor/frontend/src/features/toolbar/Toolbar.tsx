import { useState } from "react";
import type { SensorKind, ValidationResult } from "@sensor-model";
import { api, wsLogsUrl } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

/** Runtime validation (Gazebo + topic checks) often exceeds 2 minutes. */
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
  const topics = v.details?.topics as Record<string, string> | undefined;
  if (topics) {
    const ok = Object.values(topics).filter((t) => t === "ok").length;
    log(`  topics: ${ok}/${Object.keys(topics).length} publishing`);
  }
  const duration = v.details?.durationS as number | undefined;
  if (duration != null) {
    log(`  duration: ${duration}s`);
  }
}

const SENSOR_KINDS: SensorKind[] = ["imu", "contact", "lidar", "odom"];

export function Toolbar() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setModel = useEditorStore((s) => s.setModel);
  const setSelection = useEditorStore((s) => s.setSelection);
  const log = useEditorStore((s) => s.log);
  const [busy, setBusy] = useState(false);
  const [addKind, setAddKind] = useState<SensorKind>("imu");

  const defaultLink =
    selection?.kind === "link"
      ? selection.name
      : selection?.kind === "sensor"
        ? model?.sensors.find((s) => s.id === selection.id)?.parentLink
        : model?.linkNames[0];

  const addSensor = async () => {
    if (!project || !defaultLink) return;
    setBusy(true);
    try {
      const m = await api.addSensor(project, { kind: addKind, parentLink: defaultLink });
      setModel(m);
      const added = m.sensors[m.sensors.length - 1];
      if (added) setSelection({ kind: "sensor", id: added.id });
      log(`Added ${addKind} on ${defaultLink}`);
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const deleteSelected = async () => {
    if (!project || selection?.kind !== "sensor") return;
    setBusy(true);
    try {
      const m = await api.deleteSensor(project, selection.id);
      setModel(m);
      setSelection(null);
      log("Sensor removed");
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
        log(`Validation failed (${v.errors.length} errors)`);
        v.errors.slice(0, 5).forEach((e) => log(`  · ${e.message}`));
        return;
      }
      v.warnings.slice(0, 3).forEach((w) => log(`  ⚠ ${w.message}`));
      const { task_id } = await api.exportRl(project);
      log("Exporting RL package…");
      const t = await waitForTask(task_id);
      if (t?.status === "completed") {
        log("Export complete");
        if (t.result?.exportValidation) {
          logValidationResult(log, "Export validation", t.result.exportValidation as ValidationResult);
        }
      } else if (t?.status === "failed") {
        log("Export failed");
        if (t.result?.exportValidation) {
          logValidationResult(
            log,
            "Export validation",
            t.result.exportValidation as ValidationResult
          );
        } else if (t.result && "error" in t.result) {
          log(String(t.result.error));
        }
      } else {
        log("Export timed out waiting for backend — see console for progress");
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
        <span className="toolbar-label">Add</span>
        <select
          className="toolbar-select"
          value={addKind}
          disabled={!project || busy || !defaultLink}
          onChange={(e) => setAddKind(e.target.value as SensorKind)}
        >
          {SENSOR_KINDS.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy || !defaultLink}
          onClick={() => void addSensor()}
        >
          Add sensor
        </button>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy || selection?.kind !== "sensor"}
          onClick={() => void deleteSelected()}
        >
          Delete
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
          className="toolbar-btn primary"
          disabled={!project || busy}
          onClick={() => void runExport()}
        >
          RL package
        </button>
      </div>

      {busy && <span className="toolbar-busy">Working…</span>}
    </div>
  );
}
