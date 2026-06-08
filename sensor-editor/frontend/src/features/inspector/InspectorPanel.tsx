import { SENSOR_KIND_LABELS, SENSOR_PARAM_HINTS } from "@sensor-model";
import { FieldLabel } from "../../components/FieldLabel";
import { NumberField } from "../../components/NumberField";
import { TextField } from "../../components/TextField";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

const H = SENSOR_PARAM_HINTS;

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

  const poseHints = [H.poseX, H.poseY, H.poseZ] as const;
  const rpyHints = [H.roll, H.pitch, H.yaw] as const;

  return (
    <div className="unity-panel inspector-panel">
      <div className="panel-header">Inspector</div>

      <section className="inspector-section">
        <h3>ROS topics</h3>
        <div className="inspector-row">
          <FieldLabel label="Prefix" hint={H.topicPrefix} />
          <TextField
            className="field-input"
            value={model.topicPrefix}
            title={H.topicPrefix}
            onCommit={(v) => void patchTopicConfig({ topicPrefix: v })}
          />
        </div>
        <div className="inspector-row">
          <FieldLabel label="GZ model" hint={H.gzModelName} />
          <TextField
            className="field-input"
            value={model.gzModelName}
            title={H.gzModelName}
            onCommit={(v) => void patchTopicConfig({ gzModelName: v })}
          />
        </div>
        <NumberField
          label="Default Hz"
          hint={H.updateRateDefault}
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
            <FieldLabel label="Enabled" hint={H.enabled} />
            <input
              type="checkbox"
              checked={sensor.enabled}
              title={H.enabled}
              onChange={(e) => void patchSensor({ enabled: e.target.checked })}
            />
          </div>
          <div className="inspector-row">
            <FieldLabel label="Parent link" hint={H.parentLink} />
            <select
              className="field-input"
              value={sensor.parentLink}
              title={H.parentLink}
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
            <FieldLabel label="ROS topic" hint={H.rosTopic} />
            <TextField
              className="field-input"
              value={sensor.rosTopic}
              title={H.rosTopic}
              onCommit={(v) => void patchSensor({ rosTopic: v })}
            />
          </div>
          <NumberField
            label="Update Hz"
            hint={H.updateRate}
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
              hint={poseHints[i]}
              value={sensor.pose.xyz[i]}
              step={0.01}
              onChange={(v) => patchPose("xyz", i, v)}
            />
          ))}
          {(["roll", "pitch", "yaw"] as const).map((label, i) => (
            <NumberField
              key={label}
              label={label}
              hint={rpyHints[i]}
              value={sensor.pose.rpy[i]}
              step={0.01}
              onChange={(v) => patchPose("rpy", i, v)}
            />
          ))}

          {sensor.kind === "imu" && sensor.imu && (
            <div className="inspector-row">
              <FieldLabel label="Orientation" hint={H.enableOrientation} />
              <input
                type="checkbox"
                checked={sensor.imu.enableOrientation}
                title={H.enableOrientation}
                onChange={(e) =>
                  void patchSensor({ imu: { ...sensor.imu!, enableOrientation: e.target.checked } })
                }
              />
            </div>
          )}

          {sensor.kind === "contact" && sensor.contact && (
            <div className="inspector-row">
              <FieldLabel label="Collision" hint={H.collisionName} />
              <TextField
                className="field-input"
                value={sensor.contact.collisionName}
                title={H.collisionName}
                onCommit={(v) =>
                  void patchSensor({ contact: { ...sensor.contact!, collisionName: v } })
                }
              />
            </div>
          )}

          {sensor.kind === "lidar" && sensor.lidar && (
            <>
              <NumberField
                label="Samples"
                hint={H.samples}
                value={sensor.lidar.samples}
                step={1}
                min={1}
                onChange={(v) => void patchSensor({ lidar: { ...sensor.lidar!, samples: Math.round(v) } })}
              />
              <NumberField
                label="Min range"
                hint={H.minRange}
                value={sensor.lidar.minRange}
                step={0.1}
                min={0}
                onChange={(v) => void patchSensor({ lidar: { ...sensor.lidar!, minRange: v } })}
              />
              <NumberField
                label="Max range"
                hint={H.maxRange}
                value={sensor.lidar.maxRange}
                step={0.5}
                min={0.1}
                onChange={(v) => void patchSensor({ lidar: { ...sensor.lidar!, maxRange: v } })}
              />
              <NumberField
                label="H. FOV"
                hint={H.horizontalFov}
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
                <FieldLabel label="Odom frame" hint={H.odomFrame} />
                <TextField
                  className="field-input"
                  placeholder={`${model.gzModelName}/odom`}
                  value={sensor.odom.odomFrame}
                  title={H.odomFrame}
                  onCommit={(v) =>
                    void patchSensor({ odom: { ...sensor.odom!, odomFrame: v } })
                  }
                />
              </div>
              <div className="inspector-row">
                <FieldLabel label="Base frame" hint={H.robotBaseFrame} />
                <TextField
                  className="field-input"
                  value={sensor.odom.robotBaseFrame || sensor.parentLink}
                  title={H.robotBaseFrame}
                  onCommit={(v) =>
                    void patchSensor({ odom: { ...sensor.odom!, robotBaseFrame: v } })
                  }
                />
              </div>
              <NumberField
                label="Dimensions"
                hint={H.dimensions}
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
                hint={H.noiseStddev}
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
