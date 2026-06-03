import { useCallback, useEffect, useMemo, useState } from "react";
import type { Joint, Pose } from "@robot-model";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

function movableJoints(joints: Joint[]): Joint[] {
  return joints.filter((j) => j.type !== "fixed").sort((a, b) => a.name.localeCompare(b.name));
}

export function PoseEditorPanel() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);
  const [pose, setPose] = useState<Pose | null>(null);
  const [busy, setBusy] = useState(false);

  const joints = useMemo(() => (model ? movableJoints(model.joints) : []), [model]);

  const reload = useCallback(async () => {
    if (!project) return;
    const r = await api.getDefaultPose(project);
    setModel(r.model);
    setPose(r.pose);
  }, [project, setModel]);

  useEffect(() => {
    reload().catch(() => {});
  }, [reload]);

  const withBusy = async (label: string, fn: () => Promise<void>) => {
    if (!project) return;
    setBusy(true);
    try {
      await fn();
      if (label) log(label);
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const onJointChange = (jointId: string, value: number) => {
    if (!project || !pose) return;
    withBusy("", async () => {
      const r = await api.updatePoseJoint(project, pose.id, jointId, value);
      setModel(r.model);
      setPose(r.pose);
    });
  };

  if (!project || !model) {
    return <div className="pose-editor empty">Select a project to edit the default pose.</div>;
  }

  return (
    <div className="pose-editor">
      <header className="pose-editor-header">
        <h2>Default Pose</h2>
        <p className="pose-editor-hint">
          Adjust joint angles for spawn and episode reset during training. Export geometry to write
          geo_&lt;project&gt;_default_pose.yaml.
        </p>
      </header>

      <div className="pose-editor-actions">
        <button
          type="button"
          disabled={busy || !pose}
          onClick={() =>
            withBusy("Saved default pose", async () => {
              if (!pose) return;
              const r = await api.savePose(project, pose.id);
              setPose(r);
              await reload();
            })
          }
        >
          Save pose
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            withBusy("Reset to suggested stand pose", async () => {
              const r = await api.resetDefaultPoseStand(project);
              setModel(r.model);
              setPose(r.pose);
            })
          }
        >
          Reset to stand
        </button>
      </div>

      {pose && <div className="pose-name">Pose: {pose.name}</div>}

      <div className="pose-joint-list">
        {joints.map((j) => (
          <label key={j.id} className="pose-joint-row">
            <span className="pose-joint-label" title={j.name}>
              {j.name}
            </span>
            <input
              type="range"
              min={j.lowerLimit}
              max={j.upperLimit}
              step={0.01}
              value={j.defaultValue}
              disabled={busy}
              onChange={(e) => onJointChange(j.id, parseFloat(e.target.value))}
            />
            <input
              type="number"
              className="pose-joint-value"
              min={j.lowerLimit}
              max={j.upperLimit}
              step={0.01}
              value={j.defaultValue}
              disabled={busy}
              onChange={(e) => onJointChange(j.id, parseFloat(e.target.value))}
            />
          </label>
        ))}
        {joints.length === 0 && <p className="pose-empty">No movable joints on this robot.</p>}
      </div>
    </div>
  );
}
