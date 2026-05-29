import {
  PROFILE_IMPLEMENTED,
  PROFILE_LABELS,
  SIM_CONTROLLER_LABELS,
  DEFAULT_SIM_CONTROLLER,
} from "@control-model";
import { useEditorStore } from "../../stores/editorStore";

export function SummaryPanel() {
  const model = useEditorStore((s) => s.model);

  if (!model) {
    return (
      <div className="summary-panel empty">
        <h2>Control Editor</h2>
        <p>Import a physics URDF to auto-generate position-control configuration for ROS2 / Gazebo.</p>
        <ol>
          <li>Geometry Editor → export geo URDF</li>
          <li>Physics Editor → export phy URDF</li>
          <li>Control Editor → import phy URDF → export ros2_control</li>
        </ol>
      </div>
    );
  }

  const enabled = model.actuatedJoints.filter((j) => j.enabled);

  return (
    <div className="summary-panel">
      <h2>{model.robotName}</h2>
      <p className="summary-profile">
        {model.trainingProfile} — {PROFILE_LABELS[model.trainingProfile]}
      </p>
      {!PROFILE_IMPLEMENTED[model.trainingProfile] && (
        <p className="summary-warn">This profile is a placeholder. Use ProfileA to export.</p>
      )}
      <div className="summary-stats">
        <div>
          <span className="stat-value">{enabled.length}</span>
          <span className="stat-label">actuated joints</span>
        </div>
        <div>
          <span className="stat-value">{model.updateRate}</span>
          <span className="stat-label">Hz</span>
        </div>
        <div>
          <span className="stat-value stat-value-sm">
            {SIM_CONTROLLER_LABELS[model.controllerType] ??
              SIM_CONTROLLER_LABELS[DEFAULT_SIM_CONTROLLER]}
          </span>
          <span className="stat-label">sim controller</span>
        </div>
      </div>
      <table className="joint-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Joint</th>
            <th>Kp</th>
            <th>Kd</th>
            <th>Default</th>
          </tr>
        </thead>
        <tbody>
          {enabled.map((j, i) => (
            <tr key={j.name}>
              <td>{i + 1}</td>
              <td>{j.name}</td>
              <td>{j.kp.toFixed(2)}</td>
              <td>{j.kd.toFixed(2)}</td>
              <td>{j.defaultPosition.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {model.sourceUrdf && (
        <p className="summary-source">Source: {model.sourceUrdf}</p>
      )}
    </div>
  );
}
