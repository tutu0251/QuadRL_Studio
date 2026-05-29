import { useState } from "react";
import { api } from "../../api/client";
import { PROFILE_IMPLEMENTED, type TrainingProfile } from "@control-model";
import { useEditorStore } from "../../stores/editorStore";

async function pollTask(taskId: string) {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const t = await api.getTask(taskId);
    if (t.status === "completed" || t.status === "failed") return t;
  }
  return null;
}

const PROFILES: TrainingProfile[] = ["ProfileA", "ProfileB", "ProfileC"];

export function Toolbar() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);
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
        log(`Validation failed (${v.errors.length} errors)`);
        v.errors.slice(0, 5).forEach((e) => log(`  · ${e.message}`));
        return;
      }
      v.warnings.slice(0, 3).forEach((w) => log(`  ⚠ ${w.message}`));
      const { task_id } = await api.exportRos2Control(project);
      log("Exporting ros2_control…");
      const t = await pollTask(task_id);
      if (t?.status === "completed") {
        log("Export complete");
        if (t.result) {
          Object.values(t.result).forEach((path) => log(`  → ${path}`));
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
