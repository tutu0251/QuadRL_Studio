import { api } from "../../api/client";
import { MetricCard } from "../../components/MetricCard";
import { useTrainerStore } from "../../stores/trainerStore";
import { machineTier } from "../../utils/trainerMetrics";

const TIER_LABELS = {
  low: "Entry",
  mid: "Standard",
  high: "Capable",
  workstation: "Workstation",
} as const;

export function MachinePanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const m = model?.machineProfile;

  const refreshProfile = async () => {
    if (!project) return;
    try {
      await api.recommend(project);
      const updated = await api.getModel(project);
      setModel(updated);
      log("Machine profile refreshed");
    } catch (e) {
      log(String(e));
    }
  };

  if (!m) {
    return (
      <div className="unity-panel machine-panel">
        <div className="panel-header">
          <span>Host profile</span>
        </div>
        <div className="panel-empty-state">
          <p className="empty-desc">
            Load a project and run <strong>Recommend</strong> to detect CPU, RAM, and GPU.
          </p>
        </div>
      </div>
    );
  }

  const tier = machineTier(m.ramGb);
  const ramPct = m.ramGb > 0 ? Math.min(100, (m.ramGb / 64) * 100) : 0;

  return (
    <div className="unity-panel machine-panel">
      <div className="panel-header">
        <span>Host profile</span>
        <button
          type="button"
          className="header-btn"
          disabled={!project}
          onClick={() => void refreshProfile()}
        >
          Refresh
        </button>
      </div>
      <div className="machine-tier">
        <span className={`tier-pill tier-${tier}`}>{TIER_LABELS[tier]}</span>
        <span className="tier-host mono">{m.hostname}</span>
      </div>
      <div className="machine-metrics">
        <MetricCard label="CPU" value={`${m.cpuCountPhysical}c`} sub={`${m.cpuCountLogical} threads`} />
        <MetricCard label="RAM" value={`${m.ramGb.toFixed(0)} GB`} variant={tier === "low" ? "warn" : "default"} />
        <MetricCard
          label="GPU"
          value={m.gpuAvailable ? "Yes" : "None"}
          sub={m.gpuAvailable ? m.gpuName : "CPU training"}
          variant={m.gpuAvailable ? "gpu" : "default"}
        />
      </div>
      <div className="resource-bar-section">
        <div className="resource-bar-label">
          <span>Memory headroom</span>
          <span>{ramPct.toFixed(0)}%</span>
        </div>
        <div className="resource-bar">
          <div className="resource-bar-fill" style={{ width: `${ramPct}%` }} />
        </div>
      </div>
    </div>
  );
}
