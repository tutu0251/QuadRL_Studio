import {
  CONTROL_PARAM_HINTS,
  DEFAULT_SIM_CONTROLLER,
  DEFAULT_SIM_PLUGIN,
  DEFAULT_SIM_PLUGIN_CLASS,
  DEFAULT_SIM_PLUGIN_FILENAME,
  PROFILE_IMPLEMENTED,
  SIM_CONTROLLER_LABELS,
} from "@control-model";
import { FieldLabel } from "../../components/FieldLabel";
import { useEditorStore } from "../../stores/editorStore";

const C = CONTROL_PARAM_HINTS;

/** Model-level simulation / controller settings (read-mostly) + export readiness. */
export function SettingsRail() {
  const model = useEditorStore((s) => s.model);

  if (!model) {
    return (
      <section className="panel settings-rail-panel">
        <header className="panel-header">
          <h2>Simulation</h2>
        </header>
        <div className="panel-empty-state">
          <p className="empty-desc">Import a model to see controller settings.</p>
        </div>
      </section>
    );
  }

  const profileOk = PROFILE_IMPLEMENTED[model.trainingProfile];

  return (
    <section className="panel settings-rail-panel">
      <header className="panel-header">
        <div>
          <h2>Simulation</h2>
          <p className="panel-subtitle">ros2_control / Gazebo bridge configuration.</p>
        </div>
        <span className={`badge ${profileOk ? "badge-completed" : "badge-stopped"}`}>
          {profileOk ? "export ready" : "placeholder"}
        </span>
      </header>

      <div className="settings-list">
        <div className="inspector-row">
          <FieldLabel label="Gazebo bridge" hint={C.simPlugin} />
          <span className="field-value" title={C.simPlugin}>{DEFAULT_SIM_PLUGIN}</span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Plugin file" hint={C.simPlugin} />
          <span className="field-value mono">{model.simPluginFilename ?? DEFAULT_SIM_PLUGIN_FILENAME}</span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Plugin class" hint={C.simPlugin} />
          <span className="field-value mono">{model.simPluginClass ?? DEFAULT_SIM_PLUGIN_CLASS}</span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Hardware" hint={C.hardwarePlugin} />
          <span className="field-value mono">{model.hardwarePlugin}</span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Sim controller" hint={C.controllerType} />
          <span className="field-value" title={C.controllerType}>
            {SIM_CONTROLLER_LABELS[model.controllerType] ?? SIM_CONTROLLER_LABELS[DEFAULT_SIM_CONTROLLER]}
          </span>
        </div>
        <div className="inspector-row">
          <FieldLabel label="Update rate" hint={C.updateRate} />
          <span className="field-value">{model.updateRate} Hz</span>
        </div>
      </div>

      <p className="panel-hint">
        Position commands via{" "}
        <span className="mono">joint_trajectory_controller/JointTrajectoryController</span>.
      </p>
    </section>
  );
}
