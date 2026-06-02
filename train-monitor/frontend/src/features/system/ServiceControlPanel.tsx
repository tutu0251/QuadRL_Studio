import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client";
import type { ServicesStatus } from "../../types";

const POLL_MS = 5000;

function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return "—";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function overallLabel(overall: ServicesStatus["overall"]): string {
  if (overall === "running") return "All services up";
  if (overall === "partial") return "Some services down";
  return "Services stopped";
}

function stateBadge(state: "running" | "partial" | "stopped"): string {
  if (state === "running") return "ok";
  if (state === "partial") return "warn";
  return "bad";
}

export function ServiceControlPanel() {
  const [status, setStatus] = useState<ServicesStatus | null>(null);
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.servicesStatus();
      setStatus(data);
      setLive(true);
    } catch {
      setLive(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const restartServers = async () => {
    if (!window.confirm("Restart all QuadRL Studio backends and frontends? The page will disconnect briefly.")) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const r = await api.restartServices("all", 2);
      setMessage(r.message);
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  };

  const rebootMachine = async () => {
    if (
      !window.confirm(
        "Reboot this training machine? All running jobs will stop. The machine will restart in a few seconds."
      )
    ) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const r = await api.rebootMachine(5);
      setMessage(r.message);
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  };

  const trainMonitor = status?.services.find((s) => s.id === "train-monitor");
  const rlTrainer = status?.services.find((s) => s.id === "rl-trainer-editor");

  return (
    <section className="panel service-panel" aria-label="Machine and services">
      <header className="panel-header">
        <h2>
          Machine
          <span className={`live-dot ${live ? "on" : ""}`} title={live ? "Live" : "Offline"} />
        </h2>
        <span className={`status-pill status-${stateBadge(status?.overall ?? "stopped")}`}>
          {status ? overallLabel(status.overall) : "Checking…"}
        </span>
      </header>

      <dl className="status-grid compact">
        <dt>Host</dt>
        <dd className="mono">{status?.hostname ?? "—"}</dd>
        <dt>Uptime</dt>
        <dd>{formatUptime(status?.uptimeSeconds)}</dd>
        <dt>Boot service</dt>
        <dd>
          {status?.systemdActive == null
            ? "Not installed"
            : status.systemdActive
              ? "Enabled (running)"
              : "Installed (stopped)"}
        </dd>
        <dt>Editors</dt>
        <dd>
          {status
            ? `${status.runningCount}/${status.totalServices} fully up`
            : "—"}
        </dd>
      </dl>

      <div className="service-list">
        {[trainMonitor, rlTrainer].filter(Boolean).map((svc) => (
          <div key={svc!.id} className="service-row">
            <span className="service-name">{svc!.label}</span>
            <span className={`service-dot ${svc!.state === "running" ? "on" : svc!.state === "partial" ? "warn" : ""}`} />
            <span className="service-ports mono">
              API {svc!.backendPort} · UI {svc!.frontendPort}
            </span>
          </div>
        ))}
      </div>

      <div className="service-actions">
        <button type="button" className="btn secondary" disabled={busy} onClick={() => void refresh()}>
          Refresh status
        </button>
        <button type="button" className="btn warn" disabled={busy} onClick={() => void restartServers()}>
          Restart servers
        </button>
        <button type="button" className="btn danger" disabled={busy} onClick={() => void rebootMachine()}>
          Reboot machine
        </button>
      </div>

      {message && <p className="service-message">{message}</p>}
    </section>
  );
}
