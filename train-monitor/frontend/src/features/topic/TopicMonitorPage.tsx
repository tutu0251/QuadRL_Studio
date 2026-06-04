import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, wsTrainLogsUrl } from "../../api/client";
import { ActionButton } from "../../components/ActionButton";
import { TestSpawnBar } from "../../components/TestSpawnBar";
import { useCommandPreview } from "../../hooks/useCommandPreview";
import { useMonitorStore } from "../../stores/monitorStore";
import type { TopicEchoSample, TopicEntry, TopicWatchStatus, WorkspaceStatus } from "../../types";

type Props = {
  project: string | null;
  workspaceStatus: WorkspaceStatus | null;
  busy: boolean;
  gazeboHeadless: boolean;
  guiAvailable: boolean;
  resolvedDisplay: string | null;
  onBusy: (v: boolean) => void;
  onError: (msg: string | null) => void;
  onWorkspaceDone: (ws: WorkspaceStatus) => void;
  onGazeboHeadlessChange: (v: boolean) => void;
};

export function TopicMonitorPage({
  project,
  workspaceStatus,
  busy,
  gazeboHeadless,
  guiAvailable,
  resolvedDisplay,
  onBusy,
  onError,
  onWorkspaceDone,
  onGazeboHeadlessChange,
}: Props) {
  const topicsBundle = useMonitorStore((s) => s.topicsBundle);
  const setTopicsBundle = useMonitorStore((s) => s.setTopicsBundle);
  const spawnConfig = useMonitorStore((s) => s.spawnConfig);
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "ok" | "failed" | "pending">("all");
  const [spawnRunning, setSpawnRunning] = useState(false);
  const [spawnValid, setSpawnValid] = useState(false);
  const [topicEchoes, setTopicEchoes] = useState<Record<string, TopicEchoSample>>({});
  const [watchState, setWatchState] = useState<TopicWatchStatus["state"]>("idle");
  const autoWatchStarted = useRef(false);

  const setupPreview = useCommandPreview(project, "workspace_setup");
  const validatePreview = useCommandPreview(project, "workspace_validate_full");
  const validateExportsPreview = useCommandPreview(project, "workspace_validate_exports");
  const generatePreview = useCommandPreview(project, "workspace_generate");
  const buildPreview = useCommandPreview(project, "workspace_build");
  const watchStartPreview = useCommandPreview(project, "topics_watch_start");
  const watchStopPreview = useCommandPreview(project, "topics_watch_stop");
  const confirmTopics = topicsBundle?.topics.filter((t) => t.runtime_status === "ok").map((t) => t.topic) ?? [];
  const confirmAllPreview = useCommandPreview(project, "topics_confirm", {
    confirmed_topics: [...new Set([...(topicsBundle?.confirmed_topics ?? []), ...confirmTopics])],
  });

  const refreshTopics = async () => {
    if (!project) return;
    const bundle = await api.getTopics(project);
    setTopicsBundle(bundle);
  };

  const refreshWatchStatus = useCallback(async () => {
    if (!project) return;
    try {
      const status = await api.getTopicWatchStatus(project);
      setWatchState(status.state);
      setTopicEchoes(status.latest ?? {});
    } catch {
      setWatchState("idle");
    }
  }, [project]);

  useEffect(() => {
    refreshTopics().catch(() => {});
  }, [project, workspaceStatus?.finished_at]);

  useEffect(() => {
    refreshWatchStatus().catch(() => {});
  }, [refreshWatchStatus]);

  useEffect(() => {
    if (!project) {
      setSpawnRunning(false);
      setSpawnValid(false);
      return;
    }
    const poll = () => {
      api
        .getSpawnTestStatus(project)
        .then((status) => {
          const running = status.state === "running" || status.state === "starting";
          setSpawnRunning(running);
          setSpawnValid(status.spawn_valid);
        })
        .catch(() => {
          setSpawnRunning(false);
          setSpawnValid(false);
        });
    };
    poll();
    const id = window.setInterval(poll, 2500);
    return () => window.clearInterval(id);
  }, [project, busy]);

  useEffect(() => {
    if (!project) return;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsTrainLogsUrl());
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data) as {
          type?: string;
          topic?: string;
          entry?: TopicEchoSample;
        };
        if (data.type === "topic_echo" && data.topic && data.entry) {
          setTopicEchoes((prev) => ({ ...prev, [data.topic!]: data.entry! }));
        }
      };
    } catch {
      /* ignore */
    }
    return () => ws?.close();
  }, [project]);

  useEffect(() => {
    if (!project || !spawnValid) {
      autoWatchStarted.current = false;
      return;
    }
    if (autoWatchStarted.current || watchState === "running") return;
    autoWatchStarted.current = true;
    api
      .startTopicWatch(project)
      .then((s) => {
        setWatchState(s.state);
        setTopicEchoes(s.latest ?? {});
      })
      .catch(() => {
        autoWatchStarted.current = false;
      });
  }, [project, spawnValid, watchState]);

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

  const startTopicWatch = async () => {
    if (!project) return;
    onBusy(true);
    onError(null);
    try {
      const s = await api.startTopicWatch(project);
      setWatchState(s.state);
      setTopicEchoes(s.latest ?? {});
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const stopTopicWatch = async () => {
    if (!project) return;
    onBusy(true);
    try {
      const s = await api.stopTopicWatch(project);
      setWatchState(s.state);
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
  const simReady = spawnValid && spawnRunning;

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

      <section className="panel topic-spawn-panel">
        <header className="panel-header">
          <h2>Sim spawn</h2>
          <span className={`badge ${simReady ? "badge-completed" : spawnRunning ? "badge-running" : "badge-stopped"}`}>
            {simReady ? "robot ready" : spawnRunning ? "starting…" : "idle"}
          </span>
        </header>
        <p className="panel-hint">
          Same workspace test spawn as Spawn Monitor: <code>sim.launch.py</code>, controller warmup, then exported spawn
          joints via ros2_control.
        </p>
        {spawnConfig && (
          <p className="panel-hint mono">
            Effective spawn: x={spawnConfig.effective_spawn.x?.toFixed(3)} y={spawnConfig.effective_spawn.y?.toFixed(3)}{" "}
            z={spawnConfig.effective_spawn.z?.toFixed(3)} · delay {spawnConfig.controller_apply_delay_s}s
          </p>
        )}
        <TestSpawnBar
          project={project}
          busy={busy}
          gazeboHeadless={gazeboHeadless}
          guiAvailable={guiAvailable}
          resolvedDisplay={resolvedDisplay}
          onBusy={onBusy}
          onError={onError}
          onGazeboHeadlessChange={onGazeboHeadlessChange}
        />
      </section>

      <section className="panel topic-table-panel">
        <header className="panel-header">
          <h2>Observation Topics</h2>
          <span className={`badge ${watchState === "running" ? "badge-running" : "badge-stopped"}`}>
            {watchState === "running" ? "echo live" : "echo idle"}
          </span>
          <span className="badge badge-running">{topicsBundle?.topics.length ?? 0} topics</span>
        </header>
        <p className="panel-hint">
          After test spawn succeeds, topic echos poll automatically. Use live samples to confirm ROS2 / Gazebo Ignition
          sensor and state topics before training.
        </p>
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
            disabled={disabled || watchState === "running"}
            command={watchStartPreview.preview?.command}
            commandLoading={watchStartPreview.loading}
            onClick={() => void startTopicWatch()}
          >
            Start echo watch
          </ActionButton>
          <ActionButton
            className="btn small"
            disabled={disabled || watchState !== "running"}
            command={watchStopPreview.preview?.command}
            commandLoading={watchStopPreview.loading}
            onClick={() => void stopTopicWatch()}
          >
            Stop echo watch
          </ActionButton>
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
        <div className="table-scroll topic-echo-scroll">
          <table className="data-table topic-echo-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Topic</th>
                <th>Kind</th>
                <th>Bridge</th>
                <th>Runtime</th>
                <th>Live echo</th>
                <th>Confirmed</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <TopicRow
                  key={`${t.key}-${t.topic}`}
                  entry={t}
                  project={project}
                  disabled={disabled}
                  echo={topicEchoes[t.topic]}
                  onToggle={toggleConfirm}
                />
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
  project,
  disabled,
  echo,
  onToggle,
}: {
  entry: TopicEntry;
  project: string | null;
  disabled: boolean;
  echo?: TopicEchoSample;
  onToggle: (topic: string, confirmed: boolean) => void;
}) {
  const echoPreview = useCommandPreview(project, "topic_echo", { topic: entry.topic });
  const command = entry.echo_command || echoPreview.preview?.command;
  const liveOk = echo?.ok;
  const liveText = echo?.text?.trim() || echo?.snippet?.trim();

  return (
    <tr className={liveOk === true ? "topic-row-ok" : liveOk === false ? "topic-row-fail" : undefined}>
      <td>{entry.key}</td>
      <td className="mono">{entry.topic}</td>
      <td>{entry.kind}</td>
      <td>{entry.bridge_present ? "yes" : "no"}</td>
      <td>
        <span
          className={`badge badge-${entry.runtime_status === "ok" ? "completed" : entry.runtime_status === "failed" ? "stopped" : "running"}`}
        >
          {entry.runtime_status}
        </span>
        {entry.runtime_detail && <div className="topic-runtime-detail">{entry.runtime_detail}</div>}
      </td>
      <td className="topic-echo-cell">
        {echo ? (
          <>
            <span className={`badge ${echo.ok ? "badge-completed" : "badge-stopped"}`}>
              {echo.ok ? "message" : "no data"}
            </span>
            {echo.updated_at && (
              <time className="topic-echo-time" dateTime={echo.updated_at}>
                {new Date(echo.updated_at).toLocaleTimeString()}
              </time>
            )}
            {liveText ? <pre className="topic-echo-preview">{liveText}</pre> : <span className="topic-echo-empty">—</span>}
          </>
        ) : (
          <span className="topic-echo-empty">{simHint(entry)}</span>
        )}
        {command && <pre className="command-preview inline">{command}</pre>}
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
      </td>
    </tr>
  );
}

function simHint(entry: TopicEntry): string {
  return entry.runtime_status === "pending" ? "Start test spawn" : "Waiting for echo…";
}
