import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import { ActionButton } from "../../components/ActionButton";
import { useCommandPreview } from "../../hooks/useCommandPreview";
import { useMonitorStore } from "../../stores/monitorStore";
import type { TopicEntry, WorkspaceStatus } from "../../types";

type Props = {
  project: string | null;
  workspaceStatus: WorkspaceStatus | null;
  busy: boolean;
  onBusy: (v: boolean) => void;
  onError: (msg: string | null) => void;
  onWorkspaceDone: (ws: WorkspaceStatus) => void;
};

export function TopicMonitorPage({
  project,
  workspaceStatus,
  busy,
  onBusy,
  onError,
  onWorkspaceDone,
}: Props) {
  const topicsBundle = useMonitorStore((s) => s.topicsBundle);
  const setTopicsBundle = useMonitorStore((s) => s.setTopicsBundle);
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "ok" | "failed" | "pending">("all");

  const setupPreview = useCommandPreview(project, "workspace_setup");
  const validatePreview = useCommandPreview(project, "workspace_validate_full");
  const validateExportsPreview = useCommandPreview(project, "workspace_validate_exports");
  const generatePreview = useCommandPreview(project, "workspace_generate");
  const buildPreview = useCommandPreview(project, "workspace_build");
  const confirmTopics = topicsBundle?.topics.filter((t) => t.runtime_status === "ok").map((t) => t.topic) ?? [];
  const confirmAllPreview = useCommandPreview(project, "topics_confirm", {
    confirmed_topics: [...new Set([...(topicsBundle?.confirmed_topics ?? []), ...confirmTopics])],
  });

  const refreshTopics = async () => {
    if (!project) return;
    const bundle = await api.getTopics(project);
    setTopicsBundle(bundle);
  };

  useEffect(() => {
    refreshTopics().catch(() => {});
  }, [project, workspaceStatus?.finished_at]);

  const runWorkspace = async (fn: () => Promise<WorkspaceStatus & { command?: string }>) => {
    if (!project) return;
    onBusy(true);
    onError(null);
    try {
      const ws = await fn();
      onWorkspaceDone(ws);
      await refreshTopics();
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const toggleConfirm = async (topic: string, confirmed: boolean) => {
    if (!project || !topicsBundle) return;
    const next = confirmed
      ? [...new Set([...topicsBundle.confirmed_topics, topic])]
      : topicsBundle.confirmed_topics.filter((t) => t !== topic);
    onBusy(true);
    try {
      const r = await api.patchTopicConfirmations(project, next);
      setTopicsBundle(r);
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const confirmAllOk = async () => {
    if (!project || !topicsBundle) return;
    const okTopics = topicsBundle.topics.filter((t) => t.runtime_status === "ok").map((t) => t.topic);
    onBusy(true);
    try {
      const r = await api.patchTopicConfirmations(project, [...new Set([...topicsBundle.confirmed_topics, ...okTopics])]);
      setTopicsBundle(r);
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return (topicsBundle?.topics ?? []).filter((t) => {
      if (statusFilter !== "all" && t.runtime_status !== statusFilter) return false;
      if (!q) return true;
      return t.topic.toLowerCase().includes(q) || t.key.toLowerCase().includes(q);
    });
  }, [topicsBundle, filter, statusFilter]);

  const disabled = !project || busy;
  const running = workspaceStatus?.state === "running" || workspaceStatus?.state === "starting";
  const wsDisabled = disabled || running;

  return (
    <div className="page-grid topic-page">
      <section className="panel workspace-panel">
        <header className="panel-header">
          <h2>Workspace</h2>
          {workspaceStatus && (
            <span
              className={`badge ${workspaceStatus.training_ready ? "badge-completed" : workspaceStatus.build_ready ? "badge-running" : "badge-stopped"}`}
            >
              {workspaceStatus.training_ready ? "ready" : workspaceStatus.build_ready ? "built" : "not built"}
            </span>
          )}
        </header>
        <div className="btn-row wrap">
          <ActionButton
            className="btn primary"
            disabled={wsDisabled}
            command={setupPreview.preview?.command}
            commandLoading={setupPreview.loading}
            onClick={() => runWorkspace(() => api.workspaceSetup(project!, {}))}
          >
            Full setup
          </ActionButton>
          <ActionButton
            className="btn"
            disabled={wsDisabled}
            command={generatePreview.preview?.command}
            commandLoading={generatePreview.loading}
            onClick={() => runWorkspace(() => api.workspaceGenerate(project!))}
          >
            Generate
          </ActionButton>
          <ActionButton
            className="btn"
            disabled={wsDisabled}
            command={buildPreview.preview?.command}
            commandLoading={buildPreview.loading}
            onClick={() => runWorkspace(() => api.workspaceBuild(project!, {}))}
          >
            Build
          </ActionButton>
        </div>
        <div className="btn-row wrap">
          <ActionButton
            className="btn"
            disabled={wsDisabled}
            command={validateExportsPreview.preview?.command}
            commandLoading={validateExportsPreview.loading}
            onClick={() => runWorkspace(() => api.workspaceValidateExports(project!))}
          >
            Check exports
          </ActionButton>
          <ActionButton
            className="btn"
            disabled={wsDisabled}
            command={validatePreview.preview?.command}
            commandLoading={validatePreview.loading}
            onClick={() =>
              runWorkspace(() => api.workspaceValidate(project!, { static_only: false, skip_runtime: false }))
            }
          >
            Validate topics (runtime)
          </ActionButton>
        </div>
      </section>

      <section className="panel topic-table-panel">
        <header className="panel-header">
          <h2>Observation Topics</h2>
          <span className="badge badge-running">{topicsBundle?.topics.length ?? 0} topics</span>
        </header>
        <div className="filter-row">
          <input
            type="search"
            placeholder="Filter by topic or key…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}>
            <option value="all">All statuses</option>
            <option value="ok">OK</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
          <ActionButton
            className="btn small"
            disabled={disabled}
            command={confirmAllPreview.preview?.command}
            commandLoading={confirmAllPreview.loading}
            onClick={() => void confirmAllOk()}
          >
            Confirm all OK
          </ActionButton>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Topic</th>
                <th>Kind</th>
                <th>Bridge</th>
                <th>Runtime</th>
                <th>Confirmed</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <TopicRow key={`${t.key}-${t.topic}`} entry={t} disabled={disabled} onToggle={toggleConfirm} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function TopicRow({
  entry,
  disabled,
  onToggle,
}: {
  entry: TopicEntry;
  disabled: boolean;
  onToggle: (topic: string, confirmed: boolean) => void;
}) {
  const echoPreview = useCommandPreview(null, "topic_echo", { topic: entry.topic }, false);
  const command = entry.echo_command || echoPreview.preview?.command;

  return (
    <tr>
      <td>{entry.key}</td>
      <td className="mono">{entry.topic}</td>
      <td>{entry.kind}</td>
      <td>{entry.bridge_present ? "yes" : "no"}</td>
      <td>
        <span className={`badge badge-${entry.runtime_status === "ok" ? "completed" : entry.runtime_status === "failed" ? "stopped" : "running"}`}>
          {entry.runtime_status}
        </span>
      </td>
      <td>
        <label className="checkbox-row">
          <input
            type="checkbox"
            disabled={disabled}
            checked={entry.confirmed}
            onChange={(e) => onToggle(entry.topic, e.target.checked)}
          />
          OK
        </label>
        {command && <pre className="command-preview inline">{command}</pre>}
      </td>
    </tr>
  );
}
