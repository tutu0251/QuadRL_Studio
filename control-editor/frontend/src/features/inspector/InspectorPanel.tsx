import {
  DEFAULT_SIM_CONTROLLER,
  DEFAULT_SIM_PLUGIN,
  DEFAULT_SIM_PLUGIN_CLASS,
  DEFAULT_SIM_PLUGIN_FILENAME,
  PROFILE_IMPLEMENTED,
  PROFILE_LABELS,
  SIM_CONTROLLER_LABELS,
} from "@control-model";
import { NumberField } from "../../components/NumberField";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

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
          <span className="field-label">Gazebo bridge</span>
          <span className="field-value">{DEFAULT_SIM_PLUGIN}</span>
        </div>
        <div className="inspector-row">
          <span className="field-label">Plugin file</span>
          <span className="field-value mono">
            {model.simPluginFilename ?? DEFAULT_SIM_PLUGIN_FILENAME}
          </span>
        </div>
        <div className="inspector-row">
          <span className="field-label">Plugin class</span>
          <span className="field-value mono">
            {model.simPluginClass ?? DEFAULT_SIM_PLUGIN_CLASS}
          </span>
        </div>
        <div className="inspector-row">
          <span className="field-label">Hardware</span>
          <span className="field-value mono">{model.hardwarePlugin}</span>
        </div>
        <div className="inspector-row">
          <span className="field-label">Sim controller</span>
          <span className="field-value">
            {SIM_CONTROLLER_LABELS[model.controllerType] ??
              SIM_CONTROLLER_LABELS[DEFAULT_SIM_CONTROLLER]}
          </span>
        </div>
        <p className="inspector-hint">
          Position commands via{" "}
          <span className="mono">joint_trajectory_controller/JointTrajectoryController</span>
        </p>
        <div className="inspector-row">
          <span className="field-label">Update rate</span>
          <span className="field-value">{model.updateRate} Hz</span>
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
          <NumberField label="Kp" value={joint.kp} step={1} min={0} onChange={(v) => void patchJoint({ kp: v })} />
          <NumberField label="Kd" value={joint.kd} step={0.1} min={0} onChange={(v) => void patchJoint({ kd: v })} />
          <NumberField
            label="Default pos"
            value={joint.defaultPosition}
            step={0.01}
            onChange={(v) => void patchJoint({ defaultPosition: v })}
          />
          <NumberField
            label="Action scale"
            value={joint.actionScale}
            step={0.01}
            min={0}
            onChange={(v) => void patchJoint({ actionScale: v })}
          />
          <NumberField label="Effort" value={joint.effort} step={1} min={0} onChange={(v) => void patchJoint({ effort: v })} />
          <NumberField
            label="Velocity"
            value={joint.velocity}
            step={0.1}
            min={0}
            onChange={(v) => void patchJoint({ velocity: v })}
          />
          {joint.type !== "continuous" && (
            <>
              <NumberField
                label="Lower"
                value={joint.lowerLimit}
                step={0.01}
                onChange={(v) => void patchJoint({ lowerLimit: v })}
              />
              <NumberField
                label="Upper"
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
