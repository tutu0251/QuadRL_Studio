import {
  DEFAULT_SIM_CONTROLLER,
  PROFILE_IMPLEMENTED,
  PROFILE_LABELS,
  SIM_CONTROLLER_LABELS,
} from "@control-model";
import { useEditorStore } from "../../stores/editorStore";

/** Top dashboard band: at-a-glance control-model stats as cards. */
export function ModelSummaryBar() {
  const model = useEditorStore((s) => s.model);

  if (!model) {
    return (
      <section className="panel summary-empty">
        <header className="panel-header">
          <div>
            <h2>Control Editor</h2>
            <p className="panel-subtitle">
              Import a physics URDF to auto-generate position-control configuration for ROS2 / Gazebo.
            </p>
          </div>
        </header>
        <ol className="summary-steps">
          <li>Geometry Editor → export geo URDF</li>
          <li>Physics Editor → export phy URDF</li>
          <li>Control Editor → import phy URDF → export ros2_control</li>
        </ol>
      </section>
    );
  }

  const enabled = model.actuatedJoints.filter((j) => j.enabled);
  const profileOk = PROFILE_IMPLEMENTED[model.trainingProfile];
  const controller =
    SIM_CONTROLLER_LABELS[model.controllerType] ?? SIM_CONTROLLER_LABELS[DEFAULT_SIM_CONTROLLER];

  return (
    <section className="panel model-summary">
      <header className="panel-header">
        <div>
          <h2>{model.robotName}</h2>
          <p className="panel-subtitle">
            {model.trainingProfile} — {PROFILE_LABELS[model.trainingProfile]}
            {model.sourceUrdf ? ` · source ${model.sourceUrdf}` : ""}
          </p>
        </div>
        {!profileOk && <span className="badge badge-stopped">placeholder profile</span>}
      </header>

      {!profileOk && (
        <p className="panel-warn">This profile is a placeholder. Use ProfileA to edit gains and export.</p>
      )}

      <div className="stat-row">
        <div className="stat-card accent">
          <span className="stat-card-label">Actuated joints</span>
          <span className="stat-card-value">{enabled.length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Update rate</span>
          <span className="stat-card-value">{model.updateRate} Hz</span>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Sim controller</span>
          <span className="stat-card-value stat-card-value-sm">{controller}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Profile</span>
          <span className="stat-card-value stat-card-value-sm">{model.trainingProfile}</span>
        </div>
      </div>
    </section>
  );
}
