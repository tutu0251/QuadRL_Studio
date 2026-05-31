import { useState } from "react";
import type { SensorKind, ValidationResult } from "@sensor-model";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

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
}

const SENSOR_KINDS: SensorKind[] = ["imu", "contact", "lidar"];

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
      const t = await pollTask(task_id);
      if (t?.status === "completed") {
        log("Export complete");
        if (t.result) Object.entries(t.result).forEach(([k, v]) => log(`  ${k}: ${v}`));
        if (t.result?.sensorValidation) {
          logValidationResult(log, "Sensor runtime validation", t.result.sensorValidation as ValidationResult);
        }
      } else if (t?.status === "failed") {
        log("Export failed");
        if (t.result?.sensorValidation) {
          logValidationResult(
            log,
            "Sensor runtime validation",
            t.result.sensorValidation as ValidationResult
          );
        }
      } else {
        log("Export failed");
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
