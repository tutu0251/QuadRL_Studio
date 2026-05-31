import { api } from "../../api/client";
import { MetricCard } from "../../components/MetricCard";
import { useTrainerStore } from "../../stores/trainerStore";
import { machineTier } from "../../utils/trainerMetrics";
import { MemoryUsageGraph } from "./MemoryUsageGraph";

const TIER_LABELS = {
  low: "Entry",
  mid: "Standard",
  high: "Capable",
  workstation: "Workstation",
} as const;

function formatProfiledAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "numeric",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function MachinePanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const m = model?.machineProfile;

  const refreshProfile = async () => {
    if (!project) return;
    try {
      setModel(await api.refreshMachineProfile(project));
      log("Machine profile refreshed");
    } catch (e) {
      log(String(e));
    }
  };

  if (!m) {
    return (
      <div className="unity-panel machine-panel">
        <div className="panel-header panel-header-compact">
          <span>Host profile</span>
        </div>
        <div className="panel-empty-state compact-empty">
          <p className="empty-desc">Load a project to profile the host.</p>
        </div>
      </div>
    );
  }

  const tier = machineTier(m.ramGb);
  const ramUsedMb = m.ramUsedMb ?? Math.round((m.ramUsedGb ?? 0) * 1024);
  const ramTotalMb = m.ramTotalMb ?? Math.round(m.ramGb * 1024);

  return (
    <div className="unity-panel machine-panel">
      <div className="panel-header panel-header-compact">
        <span>Host profile</span>
        <button type="button" className="header-btn" disabled={!project} onClick={() => void refreshProfile()}>
          Refresh
        </button>
      </div>

      <div className="machine-tier">
        <span className={`tier-pill tier-${tier}`}>{TIER_LABELS[tier].toUpperCase()}</span>
        <span className="tier-host mono">{m.hostname || "localhost"}</span>
      </div>

      <div className="machine-metrics machine-metrics-column">
        <MetricCard label="CPU" value={`${m.cpuCountPhysical}c`} sub={`${m.cpuCountLogical} threads`} />
        <MetricCard
          label="RAM"
          value={`${ramTotalMb.toLocaleString()} MB`}
          sub={`${ramUsedMb.toLocaleString()} MB in use`}
          variant={tier === "low" ? "warn" : "default"}
        />
        <MetricCard
          label="GPU"
          value={m.gpuAvailable ? "Yes" : "None"}
          sub={m.gpuAvailable ? m.gpuName : "CPU training"}
          variant={m.gpuAvailable ? "gpu" : "default"}
        />
      </div>

      <MemoryUsageGraph initialTotalMb={ramTotalMb} initialUsedMb={ramUsedMb} />

      <div className="machine-details">
        <p className="detail-line">
          <span className="detail-key">Platform</span>
          <span className="detail-val">{m.platform || "—"}</span>
        </p>
        <p className="detail-line">
          <span className="detail-key">Profiled</span>
          <span className="detail-val">{formatProfiledAt(m.profiledAt)}</span>
        </p>
      </div>
    </div>
  );
}
