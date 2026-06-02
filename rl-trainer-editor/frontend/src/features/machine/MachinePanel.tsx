import { useCallback, useEffect, useState } from "react";
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

type ServiceSummary = Awaited<ReturnType<typeof api.servicesStatus>>;

function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

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
  const [services, setServices] = useState<ServiceSummary | null>(null);
  const [svcBusy, setSvcBusy] = useState(false);

  const refreshServices = useCallback(async () => {
    try {
      setServices(await api.servicesStatus());
    } catch {
      setServices(null);
    }
  }, []);

  useEffect(() => {
    void refreshServices();
    const id = window.setInterval(() => void refreshServices(), 5000);
    return () => window.clearInterval(id);
  }, [refreshServices]);

  const refreshProfile = async () => {
    if (!project) return;
    try {
      setModel(await api.refreshMachineProfile(project));
      log("Machine profile refreshed");
    } catch (e) {
      log(String(e));
    }
  };

  const restartServers = async () => {
    if (!window.confirm("Restart all QuadRL Studio backends and frontends?")) return;
    setSvcBusy(true);
    try {
      const r = await api.restartServices("all", 2);
      log(r.message);
    } catch (e) {
      log(String(e));
    } finally {
      setSvcBusy(false);
    }
  };

  const rebootMachine = async () => {
    if (!window.confirm("Reboot this training machine? All jobs will stop.")) return;
    setSvcBusy(true);
    try {
      const r = await api.rebootMachine(5);
      log(r.message);
    } catch (e) {
      log(String(e));
    } finally {
      setSvcBusy(false);
    }
  };

  const rlService = services?.services.find((s) => s.id === "rl-trainer-editor");

  if (!m) {
    return (
      <div className="unity-panel machine-panel">
        <div className="panel-header panel-header-compact">
          <span>Host profile</span>
        </div>
        <div className="panel-empty-state compact-empty">
          <p className="empty-desc">Load a project to profile the host.</p>
        </div>
        <div className="machine-service-block">
          <div className="machine-service-head">
            <span>Server status</span>
            <button type="button" className="header-btn" onClick={() => void refreshServices()}>
              Refresh
            </button>
          </div>
          <p className="detail-line">
            <span className="detail-key">Editors</span>
            <span className="detail-val">
              {services ? `${services.runningCount}/${services.totalServices} up` : "—"}
            </span>
          </p>
          <div className="machine-service-actions">
            <button type="button" className="header-btn" disabled={svcBusy} onClick={() => void restartServers()}>
              Restart servers
            </button>
            <button type="button" className="header-btn danger" disabled={svcBusy} onClick={() => void rebootMachine()}>
              Reboot machine
            </button>
          </div>
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

      <div className="machine-service-block">
        <div className="machine-service-head">
          <span>Server status</span>
          <button type="button" className="header-btn" onClick={() => void refreshServices()}>
            Refresh
          </button>
        </div>
        <p className="detail-line">
          <span className="detail-key">Uptime</span>
          <span className="detail-val">{formatUptime(services?.uptimeSeconds)}</span>
        </p>
        <p className="detail-line">
          <span className="detail-key">Editors</span>
          <span className="detail-val">
            {services ? `${services.runningCount}/${services.totalServices} up` : "—"}
          </span>
        </p>
        <p className="detail-line">
          <span className="detail-key">This editor</span>
          <span className="detail-val">
            {rlService
              ? rlService.state === "running"
                ? "Backend + frontend running"
                : rlService.state === "partial"
                  ? "Partially running"
                  : "Stopped"
              : "—"}
          </span>
        </p>
        <p className="detail-line">
          <span className="detail-key">Boot service</span>
          <span className="detail-val">
            {services?.systemdActive == null
              ? "Not installed"
              : services.systemdActive
                ? "Enabled"
                : "Stopped"}
          </span>
        </p>
        <div className="machine-service-actions">
          <button type="button" className="header-btn" disabled={svcBusy} onClick={() => void restartServers()}>
            Restart servers
          </button>
          <button type="button" className="header-btn danger" disabled={svcBusy} onClick={() => void rebootMachine()}>
            Reboot machine
          </button>
        </div>
      </div>
    </div>
  );
}
