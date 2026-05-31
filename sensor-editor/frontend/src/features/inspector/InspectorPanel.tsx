import { SENSOR_KIND_LABELS } from "@sensor-model";
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
          <p className="empty-desc">Select a sensor after importing ctrl URDF</p>
        </div>
      </div>
    );
  }

  const sensorId = selection?.kind === "sensor" ? selection.id : null;
  const sensor = sensorId ? model.sensors.find((s) => s.id === sensorId) : null;

  const patchSensor = async (body: Record<string, unknown>) => {
    if (!project || !sensorId) return;
    try {
      const m = await api.updateSensor(project, sensorId, body);
      setModel(m);
    } catch (e) {
      log(String(e));
    }
  };

  const patchTopicConfig = async (body: {
    topicPrefix?: string;
    gzModelName?: string;
    updateRateDefault?: number;
  }) => {
    if (!project) return;
    try {
      const m = await api.updateTopicConfig(project, body);
      setModel(m);
    } catch (e) {
      log(String(e));
    }
  };

  const patchPose = (axis: "xyz" | "rpy", idx: number, value: number) => {
    if (!sensor) return;
    const pose = { ...sensor.pose, [axis]: [...sensor.pose[axis]] as [number, number, number] };
    pose[axis][idx] = value;
    void patchSensor({ pose });
  };

  return (
    <div className="unity-panel inspector-panel">
      <div className="panel-header">Inspector</div>

      <section className="inspector-section">
        <h3>ROS topics</h3>
        <div className="inspector-row">
          <span className="field-label">Prefix</span>
          <input
            className="field-input"
            value={model.topicPrefix}
            onChange={(e) => void patchTopicConfig({ topicPrefix: e.target.value })}
          />
        </div>
        <div className="inspector-row">
          <span className="field-label">GZ model</span>
          <input
            className="field-input"
            value={model.gzModelName}
            onChange={(e) => void patchTopicConfig({ gzModelName: e.target.value })}
          />
        </div>
        <NumberField
          label="Default Hz"
          value={model.updateRateDefault}
          step={1}
          min={1}
          onChange={(v) => void patchTopicConfig({ updateRateDefault: v })}
        />
      </section>

      {sensor ? (
        <section className="inspector-section">
          <h3>
            {sensor.name}{" "}
            <span className="kind-badge">{SENSOR_KIND_LABELS[sensor.kind]}</span>
          </h3>
          <div className="inspector-row">
            <span className="field-label">Enabled</span>
            <input
              type="checkbox"
              checked={sensor.enabled}
              onChange={(e) => void patchSensor({ enabled: e.target.checked })}
            />
          </div>
          <div className="inspector-row">
            <span className="field-label">Parent link</span>
            <select
              className="field-input"
              value={sensor.parentLink}
              onChange={(e) => void patchSensor({ parentLink: e.target.value })}
            >
              {model.linkNames.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div className="inspector-row">
            <span className="field-label">ROS topic</span>
            <input
              className="field-input"
              value={sensor.rosTopic}
              onChange={(e) => void patchSensor({ rosTopic: e.target.value })}
            />
          </div>
          <NumberField
            label="Update Hz"
            value={sensor.updateRate}
            step={1}
            min={1}
            onChange={(v) => void patchSensor({ updateRate: v })}
          />
          <h4 className="inspector-subhead">Pose (link frame)</h4>
          {(["x", "y", "z"] as const).map((label, i) => (
            <NumberField
              key={label}
              label={label}
              value={sensor.pose.xyz[i]}
              step={0.01}
              onChange={(v) => patchPose("xyz", i, v)}
            />
          ))}
          {(["roll", "pitch", "yaw"] as const).map((label, i) => (
            <NumberField
              key={label}
              label={label}
              value={sensor.pose.rpy[i]}
              step={0.01}
              onChange={(v) => patchPose("rpy", i, v)}
            />
          ))}

          {sensor.kind === "imu" && sensor.imu && (
            <div className="inspector-row">
              <span className="field-label">Orientation</span>
              <input
                type="checkbox"
                checked={sensor.imu.enableOrientation}
                onChange={(e) =>
                  void patchSensor({ imu: { ...sensor.imu!, enableOrientation: e.target.checked } })
                }
              />
            </div>
          )}

          {sensor.kind === "contact" && sensor.contact && (
            <div className="inspector-row">
              <span className="field-label">Collision</span>
              <input
                className="field-input"
                value={sensor.contact.collisionName}
                onChange={(e) =>
                  void patchSensor({ contact: { ...sensor.contact!, collisionName: e.target.value } })
                }
              />
            </div>
          )}

          {sensor.kind === "lidar" && sensor.lidar && (
            <>
              <NumberField
                label="Samples"
                value={sensor.lidar.samples}
                step={1}
                min={1}
                onChange={(v) => void patchSensor({ lidar: { ...sensor.lidar!, samples: Math.round(v) } })}
              />
              <NumberField
                label="Min range"
                value={sensor.lidar.minRange}
                step={0.1}
                min={0}
                onChange={(v) => void patchSensor({ lidar: { ...sensor.lidar!, minRange: v } })}
              />
              <NumberField
                label="Max range"
                value={sensor.lidar.maxRange}
                step={0.5}
                min={0.1}
                onChange={(v) => void patchSensor({ lidar: { ...sensor.lidar!, maxRange: v } })}
              />
              <NumberField
                label="H. FOV"
                value={sensor.lidar.horizontalFov}
                step={0.1}
                min={0.1}
                onChange={(v) => void patchSensor({ lidar: { ...sensor.lidar!, horizontalFov: v } })}
              />
            </>
          )}

          {sensor.kind === "odom" && sensor.odom && (
            <>
              <div className="inspector-row">
                <span className="field-label">Odom frame</span>
                <input
                  className="field-input"
                  placeholder={`${model.gzModelName}/odom`}
                  value={sensor.odom.odomFrame}
                  onChange={(e) =>
                    void patchSensor({ odom: { ...sensor.odom!, odomFrame: e.target.value } })
                  }
                />
              </div>
              <div className="inspector-row">
                <span className="field-label">Base frame</span>
                <input
                  className="field-input"
                  value={sensor.odom.robotBaseFrame || sensor.parentLink}
                  onChange={(e) =>
                    void patchSensor({ odom: { ...sensor.odom!, robotBaseFrame: e.target.value } })
                  }
                />
              </div>
              <NumberField
                label="Dimensions"
                value={sensor.odom.dimensions}
                step={1}
                min={2}
                max={3}
                onChange={(v) =>
                  void patchSensor({ odom: { ...sensor.odom!, dimensions: Math.round(v) } })
                }
              />
              <NumberField
                label="Noise σ"
                value={sensor.odom.noiseStddev}
                step={0.01}
                min={0}
                onChange={(v) => void patchSensor({ odom: { ...sensor.odom!, noiseStddev: v } })}
              />
            </>
          )}
        </section>
      ) : selection?.kind === "link" ? (
        <div className="panel-empty-state">
          <p className="empty-desc">Link: {selection.name}</p>
          <p className="empty-desc">Use toolbar to add a sensor on this link</p>
        </div>
      ) : (
        <div className="panel-empty-state">
          <p className="empty-desc">Select a sensor in the hierarchy</p>
        </div>
      )}
    </div>
  );
}
