import { SENSOR_KIND_LABELS } from "@sensor-model";
import type { SensorKind } from "@sensor-model";
import { useEditorStore } from "../../stores/editorStore";

export function SummaryPanel() {
  const model = useEditorStore((s) => s.model);

  if (!model) {
    return (
      <div className="summary-panel empty">
        <h2>Sensor Editor</h2>
        <p>
          Import a control package (ctrl_* ros2_control URDF) and configure IMU, contact, and lidar
          sensors for Gazebo Fortress RL training.
        </p>
        <ol>
          <li>Geometry Editor → geo URDF</li>
          <li>Physics Editor → phy URDF</li>
          <li>Control Editor → ctrl ros2_control package</li>
          <li>Sensor Editor → import ctrl → export sens_* RL package</li>
        </ol>
      </div>
    );
  }

  const enabled = model.sensors.filter((s) => s.enabled);
  const byKind = (k: SensorKind) => enabled.filter((s) => s.kind === k).length;

  return (
    <div className="summary-panel">
      <h2>{model.robotName}</h2>
      <p className="summary-profile">Gazebo Fortress · {model.topicPrefix}</p>
      <div className="summary-stats">
        <div>
          <span className="stat-value">{enabled.length}</span>
          <span className="stat-label">sensors</span>
        </div>
        <div>
          <span className="stat-value">{model.linkNames.length}</span>
          <span className="stat-label">links</span>
        </div>
        <div>
          <span className="stat-value">{byKind("imu")}</span>
          <span className="stat-label">IMU</span>
        </div>
        <div>
          <span className="stat-value">{byKind("contact")}</span>
          <span className="stat-label">contact</span>
        </div>
        <div>
          <span className="stat-value">{byKind("lidar")}</span>
          <span className="stat-label">lidar</span>
        </div>
      </div>
      <table className="joint-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Kind</th>
            <th>Link</th>
            <th>ROS topic</th>
            <th>Hz</th>
          </tr>
        </thead>
        <tbody>
          {enabled.map((s) => (
            <tr key={s.id}>
              <td>{s.name}</td>
              <td>{SENSOR_KIND_LABELS[s.kind]}</td>
              <td>{s.parentLink}</td>
              <td className="mono-cell">{s.rosTopic}</td>
              <td>{s.updateRate}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="export-hints">
        <p className="summary-source">Exports (on RL package export):</p>
        <ul>
          <li>
            <code>sens_{model.projectName}_rl.urdf</code>
          </li>
          <li>
            <code>sens_{model.projectName}.sdf</code>
          </li>
          <li>
            <code>sens_{model.projectName}_bridge.yaml</code>
          </li>
          <li>
            <code>sens_{model.projectName}_observations.yaml</code>
          </li>
        </ul>
      </div>
      {model.sourceCtrlUrdf && <p className="summary-source">Source: {model.sourceCtrlUrdf}</p>}
    </div>
  );
}
