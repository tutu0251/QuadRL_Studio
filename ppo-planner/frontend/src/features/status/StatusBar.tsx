import { usePlannerStore } from "../../stores/plannerStore";
import { batchDividesRollout, resolvedDevice, rolloutSize } from "../../utils/ppoMetrics";

export function StatusBar({ connected }: { connected: boolean }) {
  const project = usePlannerStore((s) => s.project);
  const model = usePlannerStore((s) => s.model);

  const rollout = model ? rolloutSize(model.params) : 0;
  const batchOk = model ? batchDividesRollout(model.params) : true;
  const device = model ? resolvedDevice(model.params, model.machineProfile) : null;

  return (
    <footer className="status-bar">
      <span
        className={`status-dot ${connected ? "online" : "offline"}`}
        title={connected ? "API connected" : "API offline"}
      />
      <span className="status-item">{connected ? "Connected" : "Offline"}</span>
      <span className="status-sep">|</span>
      <span className="status-item">{project ? `Project: ${project}` : "No project"}</span>
      {model && device && (
        <>
          <span className="status-sep">|</span>
          <span className="status-item">{device}</span>
          <span className="status-sep">|</span>
          <span className={`status-item ${batchOk ? "" : "status-warn"}`}>
            rollout {rollout}
            {!batchOk && " ⚠"}
          </span>
        </>
      )}
      <span className="status-spacer" />
      <span className="status-item muted">ppo_*_config.yaml</span>
    </footer>
  );
}
