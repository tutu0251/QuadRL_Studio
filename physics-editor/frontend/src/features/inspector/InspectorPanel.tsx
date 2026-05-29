import { useCallback, useEffect, useState } from "react";
import type { CollisionFriction, Inertial, Link, RobotModel } from "@robot-model";
import { api } from "../../api/client";
import { Foldout } from "../../components/Foldout";
import { FrictionParamRow } from "../../components/FrictionParamRow";
import { InertiaTensorField } from "../../components/InertiaTensorField";
import { NumberField } from "../../components/NumberField";
import { Vector3Field } from "../../components/Vector3Field";
import { useEditorStore } from "../../stores/editorStore";

function inertialDirty(a: Inertial, b: Inertial): boolean {
  return JSON.stringify(a) !== JSON.stringify(b);
}

function InertialSection({
  link,
  project,
  onSaved,
}: {
  link: Link;
  project: string;
  onSaved: () => void;
}) {
  const [draft, setDraft] = useState(link.inertial);
  const [density, setDensity] = useState(1000);
  const [saving, setSaving] = useState(false);
  const dirty = inertialDirty(draft, link.inertial);

  useEffect(() => setDraft(link.inertial), [link.inertial]);

  const save = async () => {
    setSaving(true);
    try {
      await api.updateInertial(project, link.id, {
        ...draft,
        com: draft.com,
        comRotation: draft.comRotation,
      });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Foldout title="Inertial (SI)" defaultOpen>
      <NumberField label="Mass" value={draft.mass} onChange={(mass) => setDraft({ ...draft, mass })} step={0.01} min={0.001} hint="kg" />
      <Vector3Field label="COM" value={draft.com} onChange={(com) => setDraft({ ...draft, com })} />
      <InertiaTensorField
        value={draft}
        onChange={(tensor) => setDraft({ ...draft, ...tensor })}
      />
      <div className="btn-row compact">
        <button type="button" className="small-btn" disabled={!dirty} onClick={() => setDraft(link.inertial)}>
          Reset
        </button>
        <button type="button" className="small-btn primary" disabled={!dirty || saving} onClick={() => void save()}>
          {saving ? "Saving…" : "Apply"}
        </button>
      </div>
      <div className="estimate-row">
        <NumberField label="Density" value={density} onChange={setDensity} step={10} hint="kg/m³ for auto-estimate" />
        <button
          type="button"
          className="small-btn"
          onClick={() => void api.estimateLink(project, link.id, density).then(onSaved)}
        >
          Estimate from geometry
        </button>
      </div>
    </Foldout>
  );
}

function normalizeFriction(fr: CollisionFriction): CollisionFriction {
  return {
    mu: fr.mu,
    mu2: fr.mu2,
    kp: fr.kp,
    kd: fr.kd,
    enabled: fr.enabled ?? false,
    useMu: fr.useMu ?? true,
    useMu2: fr.useMu2 ?? true,
    useKp: fr.useKp ?? false,
    useKd: fr.useKd ?? false,
  };
}

function FrictionSection({ link, project, onSaved }: { link: Link; project: string; onSaved: () => void }) {
  const [fr, setFr] = useState(() => normalizeFriction(link.friction));
  const saved = normalizeFriction(link.friction);
  const dirty = JSON.stringify(fr) !== JSON.stringify(saved);

  useEffect(() => setFr(normalizeFriction(link.friction)), [link.friction]);

  return (
    <Foldout title="Collision friction (Gazebo)">
      <div className="friction-panel-master">
        <button
          type="button"
          className={`param-toggle panel-toggle ${fr.enabled ? "on" : "off"}`}
          onClick={() => setFr({ ...fr, enabled: !fr.enabled })}
          title={fr.enabled ? "Export collision friction for this link" : "Ignore entire friction block"}
          aria-pressed={fr.enabled}
        >
          {fr.enabled ? "ON" : "—"}
        </button>
        <div className="friction-panel-master-label">
          <span className="master-title">Use collision friction</span>
          <span className="master-hint">
            {fr.enabled ? "Enable per-parameter toggles below" : "Whole panel ignored on export"}
          </span>
        </div>
      </div>
      <div className={`friction-params-block ${fr.enabled ? "" : "panel-disabled"}`}>
        <FrictionParamRow
          label="μ₁"
          flag="useMu"
          valueKey="mu"
          friction={fr}
          onChange={setFr}
          panelEnabled={fr.enabled}
          step={0.05}
          min={0}
        />
        <FrictionParamRow
          label="μ₂"
          flag="useMu2"
          valueKey="mu2"
          friction={fr}
          onChange={setFr}
          panelEnabled={fr.enabled}
          step={0.05}
          min={0}
        />
        <FrictionParamRow
          label="kp"
          flag="useKp"
          valueKey="kp"
          friction={fr}
          onChange={setFr}
          panelEnabled={fr.enabled}
          step={1000}
        />
        <FrictionParamRow
          label="kd"
          flag="useKd"
          valueKey="kd"
          friction={fr}
          onChange={setFr}
          panelEnabled={fr.enabled}
          step={0.1}
        />
      </div>
      <label className="checkbox-field">
        <input
          type="checkbox"
          checked={link.isFoot}
          onChange={(e) => void api.setFoot(project, link.id, e.target.checked).then(onSaved)}
        />
        Mark as foot link (validation)
      </label>
      <button
        type="button"
        className="small-btn primary full-width"
        disabled={!dirty}
        onClick={() => void api.updateFriction(project, link.id, fr).then(onSaved)}
      >
        Apply friction
      </button>
    </Foldout>
  );
}

function JointDynamicsSection({ model, project, onSaved }: { model: RobotModel; project: string; onSaved: () => void }) {
  const selection = useEditorStore((s) => s.selection);
  const joint = selection?.kind === "link" ? model.joints.find((j) => j.childLinkId === selection.id) : undefined;
  const [dyn, setDyn] = useState(joint?.dynamics);

  useEffect(() => {
    if (joint) setDyn(joint.dynamics);
  }, [joint]);

  if (!joint || !dyn) return null;

  const dirty = JSON.stringify(dyn) !== JSON.stringify(joint.dynamics);

  return (
    <Foldout title={`Joint · ${joint.name}`} defaultOpen={false}>
      <NumberField label="Damping" value={dyn.damping} onChange={(damping) => setDyn({ ...dyn, damping })} />
      <NumberField label="Friction" value={dyn.friction} onChange={(friction) => setDyn({ ...dyn, friction })} />
      <NumberField label="Effort" value={dyn.effort} onChange={(effort) => setDyn({ ...dyn, effort })} hint="N·m" />
      <NumberField label="Velocity" value={dyn.velocity} onChange={(velocity) => setDyn({ ...dyn, velocity })} hint="rad/s or m/s" />
      <button
        type="button"
        className="small-btn primary full-width"
        disabled={!dirty}
        onClick={() => void api.updateDynamics(project, joint.id, dyn).then(onSaved)}
      >
        Apply joint dynamics
      </button>
    </Foldout>
  );
}

export function InspectorPanel() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setModel = useEditorStore((s) => s.setModel);

  const reload = useCallback(async () => {
    if (!project) return;
    const m = await api.getModel(project);
    setModel(m);
    const com = await api.robotCom(project);
    useEditorStore.getState().setWholeCom(com.com);
  }, [project, setModel]);

  if (!model || !project) {
    return (
      <div className="unity-panel inspector-panel">
        <div className="panel-header">Inspector</div>
        <div className="panel-empty-state">
          <p className="empty-title">Nothing selected</p>
          <p className="empty-desc">Load a project to edit physics properties.</p>
        </div>
      </div>
    );
  }

  if (!selection || selection.kind !== "link") {
    return (
      <div className="unity-panel inspector-panel">
        <div className="panel-header">Inspector</div>
        <div className="panel-empty-state">
          <p className="empty-title">Select a link</p>
          <p className="empty-desc">Geometry is read-only. Mass, COM, inertia, and friction are editable here.</p>
        </div>
      </div>
    );
  }

  const link = model.links.find((l) => l.id === selection.id);
  if (!link) return null;

  return (
    <div className="unity-panel inspector-panel">
      <div className="panel-header">Inspector</div>
      <div className="inspector-object-header">
        <div className="inspector-name readonly">{link.name}</div>
        <div className="inspector-tags">
          <span className="inspector-type-tag">Link</span>
          {link.isFoot && <span className="inspector-type-tag foot">Foot</span>}
          <span className="inspector-type-tag muted">{link.shapes.length} shape(s)</span>
        </div>
      </div>
      <InertialSection link={link} project={project} onSaved={() => void reload()} />
      <FrictionSection link={link} project={project} onSaved={() => void reload()} />
      <JointDynamicsSection model={model} project={project} onSaved={() => void reload()} />
    </div>
  );
}
