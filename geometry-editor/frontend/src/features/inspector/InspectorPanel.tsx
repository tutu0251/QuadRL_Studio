import type { Joint, Link, PrimitiveShape, RobotModel } from "@robot-model";
import { ROBOT_PARAM_HINTS } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";
import { FieldLabel } from "../../components/FieldLabel";
import { Foldout } from "../../components/Foldout";
import { TransformSection } from "../../components/TransformSection";

const H = ROBOT_PARAM_HINTS;

function shapeScaleFromDimensions(shape: PrimitiveShape): { x: number; y: number; z: number } {
  const d = shape.dimensions;
  switch (shape.type) {
    case "box":
      return { x: d[0] ?? 0.1, y: d[1] ?? 0.1, z: d[2] ?? 0.1 };
    case "cylinder":
    case "capsule":
      return { x: d[0] ?? 0.05, y: d[1] ?? 0.1, z: d[0] ?? 0.05 };
    case "sphere":
      return { x: d[0] ?? 0.05, y: d[0] ?? 0.05, z: d[0] ?? 0.05 };
    default:
      return { x: 1, y: 1, z: 1 };
  }
}

function shapeScaleLabels(type: PrimitiveShape["type"]): [string, string, string] {
  switch (type) {
    case "box":
      return ["W", "H", "D"];
    case "cylinder":
    case "capsule":
      return ["R", "L", "R"];
    case "sphere":
      return ["R", "—", "—"];
    default:
      return ["X", "Y", "Z"];
  }
}

function parentLinkNameForLink(model: RobotModel, link: Link): string | null {
  if (!link.parentJointId) return null;
  const parentJoint = model.joints.find((j) => j.id === link.parentJointId);
  if (!parentJoint) return null;
  return model.links.find((l) => l.id === parentJoint.parentLinkId)?.name ?? null;
}

function parentLinkNameForJoint(model: RobotModel, joint: Joint): string | null {
  return model.links.find((l) => l.id === joint.parentLinkId)?.name ?? null;
}

function ParentNameField({ name }: { name: string | null }) {
  return (
    <div className="inspector-row">
      <FieldLabel label="Parent" hint={H.parent} />
      <input className="inspector-readonly" value={name ?? "—"} readOnly title={H.parent} />
    </div>
  );
}

function dimensionsFromScale(shape: PrimitiveShape, scale: { x: number; y: number; z: number }): number[] {
  switch (shape.type) {
    case "box":
      return [Math.max(0.001, scale.x), Math.max(0.001, scale.y), Math.max(0.001, scale.z)];
    case "cylinder":
    case "capsule":
      return [Math.max(0.001, scale.x), Math.max(0.001, scale.y)];
    case "sphere":
      return [Math.max(0.001, scale.x)];
    default:
      return shape.dimensions;
  }
}

export function InspectorPanel() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setModel = useEditorStore((s) => s.setModel);
  const gizmoMode = useEditorStore((s) => s.gizmoMode);
  const setGizmoMode = useEditorStore((s) => s.setGizmoMode);
  const gizmoTarget = useEditorStore((s) => s.gizmoTarget);
  const setGizmoTarget = useEditorStore((s) => s.setGizmoTarget);

  if (!model || !project) {
    return (
      <div className="unity-panel inspector-panel">
        <div className="panel-header">Inspector</div>
        <p className="panel-empty">Nothing selected</p>
      </div>
    );
  }

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

  const objectName = link?.name ?? joint?.name ?? (shapeCtx ? `${shapeCtx.shape.type}` : null);
  const objectType = link ? "Link" : joint ? "Joint" : shapeCtx ? "Shape" : null;

  if (!objectName) {
    return (
      <div className="unity-panel inspector-panel">
        <div className="panel-header">Inspector</div>
        <p className="panel-empty">Select a link, joint, or shape in the Hierarchy</p>
      </div>
    );
  }

  return (
    <div className="unity-panel inspector-panel">
      <div className="panel-header">Inspector</div>

      <div className="inspector-object-header">
        <input
          className="inspector-name"
          defaultValue={objectName}
          key={objectName + (link?.id ?? joint?.id ?? shapeCtx?.shape.id)}
          onBlur={async (e) => {
            if (link) await api.renameLink(project, link.id, e.target.value);
            else if (joint) await api.renameJoint(project, joint.id, e.target.value);
            await reload();
          }}
          readOnly={!!shapeCtx}
        />
        <span className="inspector-type-tag">{objectType}</span>
      </div>

      <Foldout title="Transform Tools">
        <div className="inspector-row">
          <span className="field-label">Gizmo</span>
          <div className="tool-toggle-group">
            {(["translate", "rotate", "scale"] as const).map((m) => (
              <button
                key={m}
                type="button"
                className={`tool-btn ${gizmoMode === m ? "active" : ""}`}
                onClick={() => setGizmoMode(m)}
                title={m}
              >
                {m[0].toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="inspector-row">
          <span className="field-label">Target</span>
          <div className="tool-toggle-group">
            {(["link", "joint", "shape"] as const).map((t) => (
              <button
                key={t}
                type="button"
                className={`tool-btn ${gizmoTarget === t ? "active" : ""}`}
                onClick={() => setGizmoTarget(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </Foldout>

      {link && <LinkInspector model={model} link={link} project={project} onUpdate={reload} />}
      {joint && <JointInspector model={model} joint={joint} project={project} onUpdate={reload} />}
      {shapeCtx && (
        <ShapeInspector
          link={shapeCtx.link}
          shape={shapeCtx.shape}
          project={project}
          onUpdate={reload}
        />
      )}
    </div>
  );
}

function LinkInspector({
  model,
  link,
  project,
  onUpdate,
}: {
  model: RobotModel;
  link: Link;
  project: string;
  onUpdate: () => Promise<void>;
}) {
  return (
    <>
      <Foldout title="Transform">
        <TransformSection
          position={link.frame.position}
          rotation={link.frame.rotation}
          onPositionChange={async (position) => {
            await api.updateLinkFrame(project, link.id, { ...link.frame, position });
            await onUpdate();
          }}
          onRotationChange={async (rotation) => {
            await api.updateLinkFrame(project, link.id, { ...link.frame, rotation });
            await onUpdate();
          }}
        />
      </Foldout>
      <Foldout title="Link">
        <ParentNameField name={parentLinkNameForLink(model, link)} />
        <div className="inspector-row">
          <span className="field-label">Shapes</span>
          <span>{link.shapes.length}</span>
        </div>
        <div className="btn-row compact">
          {(["box", "cylinder", "sphere", "capsule"] as const).map((t) => (
            <button
              key={t}
              type="button"
              className="small-btn"
              onClick={async () => {
                await api.addShape(project, link.id, t);
                await onUpdate();
              }}
            >
              + {t}
            </button>
          ))}
        </div>
        {link.shapes.map((s) => (
          <button
            key={s.id}
            type="button"
            className="hierarchy-item full-width"
            onClick={() =>
              useEditorStore.getState().setSelection({ kind: "shape", linkId: link.id, shapeId: s.id })
            }
          >
            ◇ {s.type} [{s.dimensions.map((d) => d.toFixed(2)).join(", ")}]
          </button>
        ))}
      </Foldout>
      <Foldout title="Inertial" defaultOpen={false}>
        <div className="inspector-row">
          <span className="field-label">Mass</span>
          <span>{link.inertial.mass} kg (placeholder)</span>
        </div>
      </Foldout>
    </>
  );
}

function JointInspector({
  model,
  joint,
  project,
  onUpdate,
}: {
  model: RobotModel;
  joint: Joint;
  project: string;
  onUpdate: () => Promise<void>;
}) {
  const update = async (data: Record<string, unknown>) => {
    await api.updateJoint(project, joint.id, data);
    await onUpdate();
  };

  return (
    <>
      <Foldout title="Transform">
        <TransformSection
          position={joint.originPosition}
          rotation={joint.originRotation}
          onPositionChange={async (originPosition) => {
            await update({ originPosition });
          }}
          onRotationChange={async (originRotation) => {
            await update({ originRotation });
          }}
        />
      </Foldout>
      <Foldout title="Joint">
        <ParentNameField name={parentLinkNameForJoint(model, joint)} />
        <div className="inspector-row">
          <FieldLabel label="Type" hint={H.jointType} />
          <select value={joint.type} title={H.jointType} onChange={(e) => update({ type: e.target.value })}>
            <option value="fixed">Fixed</option>
            <option value="revolute">Revolute</option>
            <option value="continuous">Continuous</option>
            <option value="prismatic">Prismatic</option>
          </select>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Default" hint={H.defaultValue} />
          <input
            type="number"
            step="0.01"
            value={joint.defaultValue}
            title={H.defaultValue}
            onChange={(e) => update({ defaultValue: +e.target.value })}
          />
        </div>
        {joint.type === "revolute" && (
          <>
            <div className="inspector-row">
              <FieldLabel label="Lower" hint={H.lowerLimit} />
              <input
                type="number"
                step="0.01"
                value={joint.lowerLimit}
                title={H.lowerLimit}
                onChange={(e) => update({ lowerLimit: +e.target.value })}
              />
            </div>
            <div className="inspector-row">
              <FieldLabel label="Upper" hint={H.upperLimit} />
              <input
                type="number"
                step="0.01"
                value={joint.upperLimit}
                title={H.upperLimit}
                onChange={(e) => update({ upperLimit: +e.target.value })}
              />
            </div>
          </>
        )}
        <Vector3FieldInline
          label="Axis"
          hint={H.axis}
          values={joint.axis}
          onChange={(axis) => update({ axis })}
        />
      </Foldout>
    </>
  );
}

function Vector3FieldInline({
  label,
  hint,
  values,
  onChange,
}: {
  label: string;
  hint?: string;
  values: { x: number; y: number; z: number };
  onChange: (v: { x: number; y: number; z: number }) => void;
}) {
  return (
    <div className="vector3-field">
      <FieldLabel label={label} hint={hint} />
      <div className="vector3-inputs">
        {(["x", "y", "z"] as const).map((axis) => (
          <label key={axis} className={`axis-${axis}`}>
            {axis.toUpperCase()}
            <input
              type="number"
              step={0.1}
              value={values[axis]}
              onChange={(e) => onChange({ ...values, [axis]: +e.target.value })}
            />
          </label>
        ))}
      </div>
    </div>
  );
}

function ShapeInspector({
  link,
  shape,
  project,
  onUpdate,
}: {
  link: Link;
  shape: PrimitiveShape;
  project: string;
  onUpdate: () => Promise<void>;
}) {
  const scale = shapeScaleFromDimensions(shape);
  const scaleLabels = shapeScaleLabels(shape.type);
  const sphereScale = shape.type === "sphere";

  return (
    <>
      <Foldout title="Transform">
        <ParentNameField name={link.name} />
        <TransformSection
          position={shape.localPosition}
          rotation={shape.localRotation}
          scale={scale}
          scaleLabels={scaleLabels}
          onPositionChange={async (localPosition) => {
            await api.updateTransform(project, link.id, shape.id, localPosition, shape.localRotation);
            await onUpdate();
          }}
          onRotationChange={async (localRotation) => {
            await api.updateTransform(project, link.id, shape.id, shape.localPosition, localRotation);
            await onUpdate();
          }}
          onScaleChange={async (s) => {
            const effective =
              shape.type === "sphere" ? { x: s.x, y: s.x, z: s.x } : s;
            const dims = dimensionsFromScale(shape, effective);
            await api.updateDimensions(project, link.id, shape.id, dims);
            await onUpdate();
          }}
        />
        {sphereScale && (
          <p className="transform-hint">Sphere uses uniform radius (X). Y/Z ignored.</p>
        )}
      </Foldout>
      <Foldout title={`${shape.type} (Primitive)`} defaultOpen={false}>
        <div className="inspector-row">
          <span className="field-label">Color</span>
          <input type="color" value={shape.color} readOnly />
        </div>
      </Foldout>
    </>
  );
}
