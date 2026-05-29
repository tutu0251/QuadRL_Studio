import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";

/** Wait for task completion. Logs stream via WebSocket (/ws/logs) in App.tsx. */
async function pollTask(taskId: string) {
  for (let i = 0; i < 60; i++) {
    const t = await api.getTask(taskId);
    if (t.status === "completed" || t.status === "failed") return t;
    await new Promise((r) => setTimeout(r, 500));
  }
  return null;
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
      await pollTask(task_id);
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
        <button type="button" disabled={!project} onClick={() => run("urdf", () => api.exportUrdf(project!))}>
          Export URDF
        </button>
        <button type="button" disabled={!project} onClick={() => run("sdf", () => api.exportSdf(project!))}>
          Export SDF
        </button>
        <button type="button" disabled={!project} onClick={() => run("both", () => api.exportBoth(project!))}>
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
