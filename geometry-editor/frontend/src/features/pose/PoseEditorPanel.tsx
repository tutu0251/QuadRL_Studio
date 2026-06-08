import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Joint, Pose } from "@robot-model";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

function movableJoints(joints: Joint[]): Joint[] {
  return joints.filter((j) => j.type !== "fixed").sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * One joint row. The slider stays responsive by tracking a local value during
 * drag and only committing to the API on release; the number input commits on
 * blur/Enter. This avoids a network request per slider tick / keystroke.
 */
function PoseJointRow({
  joint,
  disabled,
  onCommit,
}: {
  joint: Joint;
  disabled: boolean;
  onCommit: (value: number) => void;
}) {
  const [draft, setDraft] = useState(joint.defaultValue);
  const editing = useRef(false);

  useEffect(() => {
    if (!editing.current) setDraft(joint.defaultValue);
  }, [joint.defaultValue]);

  const commit = (value: number) => {
    editing.current = false;
    if (value !== joint.defaultValue) onCommit(value);
  };

  return (
    <label className="pose-joint-row">
      <span className="pose-joint-label" title={joint.name}>
        {joint.name}
      </span>
      <input
        type="range"
        min={joint.lowerLimit}
        max={joint.upperLimit}
        step={0.01}
        value={draft}
        disabled={disabled}
        onChange={(e) => {
          editing.current = true;
          setDraft(parseFloat(e.target.value));
        }}
        onPointerUp={() => commit(draft)}
        onKeyUp={() => commit(draft)}
      />
      <input
        type="number"
        className="pose-joint-value"
        min={joint.lowerLimit}
        max={joint.upperLimit}
        step={0.01}
        value={draft}
        disabled={disabled}
        onFocus={() => {
          editing.current = true;
        }}
        onChange={(e) => setDraft(parseFloat(e.target.value))}
        onBlur={() => {
          const v = Number.isFinite(draft) ? draft : joint.defaultValue;
          setDraft(v);
          commit(v);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          else if (e.key === "Escape") {
            setDraft(joint.defaultValue);
            editing.current = false;
            e.currentTarget.blur();
          }
        }}
      />
    </label>
  );
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
          <PoseJointRow
            key={j.id}
            joint={j}
            disabled={busy}
            onCommit={(v) => onJointChange(j.id, v)}
          />
        ))}
        {joints.length === 0 && <p className="pose-empty">No movable joints on this robot.</p>}
      </div>
    </div>
  );
}
