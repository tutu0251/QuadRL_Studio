import { api } from "../../api/client";
import { MetricCard } from "../../components/MetricCard";
import { usePlannerStore } from "../../stores/plannerStore";
import { machineTier } from "../../utils/ppoMetrics";

const TIER_LABELS = {
  low: "Entry",
  mid: "Standard",
  high: "Capable",
  workstation: "Workstation",
} as const;

export function MachinePanel() {
  const project = usePlannerStore((s) => s.project);
  const model = usePlannerStore((s) => s.model);
  const setModel = usePlannerStore((s) => s.setModel);
  const log = usePlannerStore((s) => s.log);
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
          <div className="empty-illustration" aria-hidden>
            ◫
          </div>
          <p className="empty-title">No profile yet</p>
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
          title="Re-detect hardware and apply recommendations"
        >
          Refresh
        </button>
      </div>

      <div className="machine-tier">
        <span className={`tier-pill tier-${tier}`}>{TIER_LABELS[tier]}</span>
        <span className="tier-host mono">{m.hostname}</span>
      </div>

      <div className="machine-metrics">
        <MetricCard
          label="CPU"
          value={`${m.cpuCountPhysical}c`}
          sub={`${m.cpuCountLogical} threads`}
        />
        <MetricCard
          label="RAM"
          value={`${m.ramGb.toFixed(0)} GB`}
          variant={tier === "low" ? "warn" : "default"}
        />
        <MetricCard
          label="GPU"
          value={m.gpuAvailable ? "Yes" : "None"}
          sub={m.gpuAvailable ? m.gpuName : "CPU training"}
          variant={m.gpuAvailable ? "gpu" : "default"}
        />
        {m.gpuAvailable && (
          <MetricCard label="VRAM" value={`${m.vramGb.toFixed(1)} GB`} variant="gpu" />
        )}
      </div>

      <div className="resource-bar-section">
        <div className="resource-bar-label">
          <span>Memory headroom (vs 64 GB ref.)</span>
          <span>{ramPct.toFixed(0)}%</span>
        </div>
        <div className="resource-bar">
          <div className="resource-bar-fill" style={{ width: `${ramPct}%` }} />
        </div>
      </div>

      <section className="machine-details">
        <p className="detail-line">
          <span className="detail-key">Platform</span>
          <span className="detail-val mono">{m.platform}</span>
        </p>
        <p className="detail-line">
          <span className="detail-key">Profiled</span>
          <span className="detail-val mono">{new Date(m.profiledAt).toLocaleString()}</span>
        </p>
      </section>
    </div>
  );
}
