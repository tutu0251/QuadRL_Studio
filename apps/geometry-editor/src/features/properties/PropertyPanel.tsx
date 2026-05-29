import type { Link, Joint, PrimitiveShape } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";

export function PropertyPanel() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setModel = useEditorStore((s) => s.setModel);
  const gizmoMode = useEditorStore((s) => s.gizmoMode);
  const setGizmoMode = useEditorStore((s) => s.setGizmoMode);
  const gizmoTarget = useEditorStore((s) => s.gizmoTarget);
  const setGizmoTarget = useEditorStore((s) => s.setGizmoTarget);

  if (!model || !project) return <p className="muted">Select an element</p>;

  const link = selection?.kind === "link" ? model.links.find((l) => l.id === selection.id) : null;
  const joint = selection?.kind === "joint" ? model.joints.find((j) => j.id === selection.id) : null;
  const shapeCtx =
    selection?.kind === "shape"
      ? {
          link: model.links.find((l) => l.id === selection.linkId)!,
          shape: model.links
            .find((l) => l.id === selection.linkId)
            ?.shapes.find((s) => s.id === selection.shapeId)!,
        }
      : null;

  const reload = async () => setModel(await api.getModel(project));

  return (
    <div className="properties">
      <section>
        <h2>Gizmo</h2>
        <div className="btn-row">
          {(["translate", "rotate", "scale"] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={gizmoMode === m ? "active" : ""}
              onClick={() => setGizmoMode(m)}
            >
              {m}
            </button>
          ))}
        </div>
        <div className="btn-row">
          {(["link", "joint", "shape"] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={gizmoTarget === t ? "active" : ""}
              onClick={() => setGizmoTarget(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      {link && <LinkProperties link={link} project={project} onUpdate={reload} />}
      {joint && <JointProperties joint={joint} project={project} onUpdate={reload} />}
      {shapeCtx && (
        <ShapeProperties
          link={shapeCtx.link}
          shape={shapeCtx.shape}
          project={project}
          onUpdate={reload}
        />
      )}
      {!link && !joint && !shapeCtx && <p className="muted">Click a link, joint, or shape</p>}
    </div>
  );
}

function NumInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label>
      {label}
      <input type="number" step="0.01" value={value} onChange={(e) => onChange(+e.target.value)} />
    </label>
  );
}

function LinkProperties({
  link,
  project,
  onUpdate,
}: {
  link: Link;
  project: string;
  onUpdate: () => void;
}) {
  const updateFrame = async (field: "position" | "rotation", axis: "x" | "y" | "z", val: number) => {
    const frame = { ...link.frame, [field]: { ...link.frame[field], [axis]: val } };
    await api.updateLinkFrame(project, link.id, frame);
    onUpdate();
  };

  return (
    <section>
      <h2>Link: {link.name}</h2>
      <label>
        Name
        <input
          defaultValue={link.name}
          onBlur={async (e) => {
            await api.renameLink(project, link.id, e.target.value);
            onUpdate();
          }}
        />
      </label>
      <p>Position</p>
      {(["x", "y", "z"] as const).map((a) => (
        <NumInput
          key={a}
          label={a}
          value={link.frame.position[a]}
          onChange={(v) => updateFrame("position", a, v)}
        />
      ))}
      <div className="btn-row">
        {(["box", "cylinder", "sphere", "capsule"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={async () => {
              await api.addShape(project, link.id, t);
              onUpdate();
            }}
          >
            +{t}
          </button>
        ))}
      </div>
      {link.shapes.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => useEditorStore.getState().setSelection({ kind: "shape", linkId: link.id, shapeId: s.id })}
        >
          {s.type}
        </button>
      ))}
    </section>
  );
}

function JointProperties({
  joint,
  project,
  onUpdate,
}: {
  joint: Joint;
  project: string;
  onUpdate: () => void;
}) {
  const update = async (data: Record<string, unknown>) => {
    await api.updateJoint(project, joint.id, data);
    onUpdate();
  };

  return (
    <section>
      <h2>Joint: {joint.name}</h2>
      <label>
        Type
        <select
          value={joint.type}
          onChange={(e) => update({ type: e.target.value })}
        >
          <option value="fixed">fixed</option>
          <option value="revolute">revolute</option>
          <option value="continuous">continuous</option>
          <option value="prismatic">prismatic</option>
        </select>
      </label>
      <p>Origin</p>
      {(["x", "y", "z"] as const).map((a) => (
        <NumInput
          key={a}
          label={`origin ${a}`}
          value={joint.originPosition[a]}
          onChange={(v) => update({ originPosition: { ...joint.originPosition, [a]: v } })}
        />
      ))}
      <p>Axis</p>
      {(["x", "y", "z"] as const).map((a) => (
        <NumInput
          key={a}
          label={`axis ${a}`}
          value={joint.axis[a]}
          onChange={(v) => update({ axis: { ...joint.axis, [a]: v } })}
        />
      ))}
      {joint.type === "revolute" && (
        <>
          <NumInput label="lower" value={joint.lowerLimit} onChange={(v) => update({ lowerLimit: v })} />
          <NumInput label="upper" value={joint.upperLimit} onChange={(v) => update({ upperLimit: v })} />
        </>
      )}
      <NumInput label="default" value={joint.defaultValue} onChange={(v) => update({ defaultValue: v })} />
    </section>
  );
}

function ShapeProperties({
  link,
  shape,
  project,
  onUpdate,
}: {
  link: Link;
  shape: PrimitiveShape;
  project: string;
  onUpdate: () => void;
}) {
  return (
    <section>
      <h2>Shape: {shape.type}</h2>
      {shape.dimensions.map((d, i) => (
        <NumInput
          key={i}
          label={`dim${i}`}
          value={d}
          onChange={async (v) => {
            const dims = [...shape.dimensions];
            dims[i] = v;
            await api.updateDimensions(project, link.id, shape.id, dims);
            onUpdate();
          }}
        />
      ))}
      <p>Local position</p>
      {(["x", "y", "z"] as const).map((a) => (
        <NumInput
          key={a}
          label={a}
          value={shape.localPosition[a]}
          onChange={async (v) => {
            await api.updateTransform(project, link.id, shape.id, { ...shape.localPosition, [a]: v }, shape.localRotation);
            onUpdate();
          }}
        />
      ))}
    </section>
  );
}
