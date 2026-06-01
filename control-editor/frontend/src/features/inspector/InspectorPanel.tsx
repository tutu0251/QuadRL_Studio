import {
  CONTROL_PARAM_HINTS,
  DEFAULT_SIM_CONTROLLER,
  DEFAULT_SIM_PLUGIN,
  DEFAULT_SIM_PLUGIN_CLASS,
  DEFAULT_SIM_PLUGIN_FILENAME,
  JOINT_PARAM_HINTS,
  PROFILE_IMPLEMENTED,
  PROFILE_LABELS,
  SIM_CONTROLLER_LABELS,
} from "@control-model";
import { FieldLabel } from "../../components/FieldLabel";
import { NumberField } from "../../components/NumberField";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

const H = JOINT_PARAM_HINTS;
const C = CONTROL_PARAM_HINTS;

export function InspectorPanel() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);

  if (!model) {
    return (
      <div className="unity-panel inspector-panel">
        <div className="panel-header">Inspector</div>
        <div className="panel-empty-state">
          <p className="empty-desc">Select a joint after importing</p>
        </div>
      </div>
    );
  }

  const profileOk = PROFILE_IMPLEMENTED[model.trainingProfile];

  if (!profileOk) {
    return (
      <div className="unity-panel inspector-panel">
        <div className="panel-header">Inspector</div>
        <div className="placeholder-box">
          <p className="empty-title">{model.trainingProfile}</p>
          <p className="empty-desc">{PROFILE_LABELS[model.trainingProfile]}</p>
          <p className="empty-desc">Switch to ProfileA for position control editing.</p>
        </div>
      </div>
    );
  }

  const jointName = selection?.kind === "joint" ? selection.name : null;
  const joint = jointName ? model.actuatedJoints.find((j) => j.name === jointName) : null;

  const patchJoint = async (body: Record<string, number | boolean>) => {
    if (!project || !jointName) return;
    try {
      const m = await api.updateJoint(project, jointName, body);
      setModel(m);
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <div className="unity-panel inspector-panel">
      <div className="panel-header">Inspector</div>

      <section className="inspector-section">
        <h3>Simulation</h3>
        <div className="inspector-row">
          <FieldLabel label="Gazebo bridge" hint={C.simPlugin} />
          <span className="field-value" title={C.simPlugin}>
            {DEFAULT_SIM_PLUGIN}
          </span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Plugin file" hint={C.simPlugin} />
          <span className="field-value mono" title={C.simPlugin}>
            {model.simPluginFilename ?? DEFAULT_SIM_PLUGIN_FILENAME}
          </span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Plugin class" hint={C.simPlugin} />
          <span className="field-value mono" title={C.simPlugin}>
            {model.simPluginClass ?? DEFAULT_SIM_PLUGIN_CLASS}
          </span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Hardware" hint={C.hardwarePlugin} />
          <span className="field-value mono" title={C.hardwarePlugin}>
            {model.hardwarePlugin}
          </span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Sim controller" hint={C.controllerType} />
          <span className="field-value" title={C.controllerType}>
            {SIM_CONTROLLER_LABELS[model.controllerType] ??
              SIM_CONTROLLER_LABELS[DEFAULT_SIM_CONTROLLER]}
          </span>
        </div>
        <p className="inspector-hint">
          Position commands via{" "}
          <span className="mono">joint_trajectory_controller/JointTrajectoryController</span>
        </p>
        <div className="inspector-row">
          <FieldLabel label="Update rate" hint={C.updateRate} />
          <span className="field-value" title={C.updateRate}>
            {model.updateRate} Hz
          </span>
        </div>
      </section>

      {joint ? (
        <section className="inspector-section">
          <h3>{joint.name}</h3>
          <div className="inspector-row">
            <span className="field-label">Type</span>
            <span className="field-value">{joint.type}</span>
          </div>
          <div className="inspector-row">
            <span className="field-label">Child link</span>
            <span className="field-value mono">{joint.childLinkName}</span>
          </div>
          <NumberField label="Kp" hint={H.kp} value={joint.kp} step={1} min={0} onChange={(v) => void patchJoint({ kp: v })} />
          <NumberField label="Kd" hint={H.kd} value={joint.kd} step={0.1} min={0} onChange={(v) => void patchJoint({ kd: v })} />
          <NumberField
            label="Default pos"
            hint={H.defaultPosition}
            value={joint.defaultPosition}
            step={0.01}
            onChange={(v) => void patchJoint({ defaultPosition: v })}
          />
          <NumberField
            label="Action scale"
            hint={H.actionScale}
            value={joint.actionScale}
            step={0.01}
            min={0}
            onChange={(v) => void patchJoint({ actionScale: v })}
          />
          <NumberField label="Effort" hint={H.effort} value={joint.effort} step={1} min={0} onChange={(v) => void patchJoint({ effort: v })} />
          <NumberField
            label="Velocity"
            hint={H.velocity}
            value={joint.velocity}
            step={0.1}
            min={0}
            onChange={(v) => void patchJoint({ velocity: v })}
          />
          {joint.type !== "continuous" && (
            <>
              <NumberField
                label="Lower"
                hint={H.lowerLimit}
                value={joint.lowerLimit}
                step={0.01}
                onChange={(v) => void patchJoint({ lowerLimit: v })}
              />
              <NumberField
                label="Upper"
                hint={H.upperLimit}
                value={joint.upperLimit}
                step={0.01}
                onChange={(v) => void patchJoint({ upperLimit: v })}
              />
            </>
          )}
        </section>
      ) : (
        <div className="panel-empty-state">
          <p className="empty-desc">Select a joint in the hierarchy</p>
        </div>
      )}
    </div>
  );
}
