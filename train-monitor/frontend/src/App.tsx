import { useCallback, useEffect, useState } from "react";
import { api, wsTrainLogsUrl } from "./api/client";
import { ConsolePanel } from "./features/console/ConsolePanel";
import { ConsoleSplitter } from "./components/ConsoleSplitter";
import { TestSpawnBar } from "./components/TestSpawnBar";
import { MetricMonitorPage } from "./features/metric/MetricMonitorPage";
import { MenuBar } from "./features/menu/MenuBar";
import { PageNav } from "./features/nav/PageNav";
import { SpawnMonitorPage } from "./features/spawn/SpawnMonitorPage";
import { StatusBar } from "./features/status/StatusBar";
import { TopicMonitorPage } from "./features/topic/TopicMonitorPage";
import { TrainingMonitorPage } from "./features/training/TrainingMonitorPage";
import { useMonitorStore } from "./stores/monitorStore";
import type { MonitorPageId, ProjectSummary, TensorBoardStatus, TrainStatus, WorkspaceStatus, WsLogPayload } from "./types";
import { normalizeLogLevel, parseLogComponent } from "./utils/logUtils";

export default function App() {
  const project = useMonitorStore((s) => s.project);
  const activePage = useMonitorStore((s) => s.activePage);
  const exports = useMonitorStore((s) => s.exports);
  const checkpoints = useMonitorStore((s) => s.checkpoints);
  const runs = useMonitorStore((s) => s.runs);
  const trainStatus = useMonitorStore((s) => s.trainStatus);
  const scalars = useMonitorStore((s) => s.scalars);
  const selectedRunId = useMonitorStore((s) => s.selectedRunId);
  const log = useMonitorStore((s) => s.log);
  const appendLog = useMonitorStore((s) => s.appendLog);
  const setProject = useMonitorStore((s) => s.setProject);
  const setActivePage = useMonitorStore((s) => s.setActivePage);
  const setExports = useMonitorStore((s) => s.setExports);
  const setCheckpoints = useMonitorStore((s) => s.setCheckpoints);
  const setRuns = useMonitorStore((s) => s.setRuns);
  const setTrainStatus = useMonitorStore((s) => s.setTrainStatus);
  const setScalars = useMonitorStore((s) => s.setScalars);
  const setSelectedRunId = useMonitorStore((s) => s.setSelectedRunId);
  const setSpawnConfig = useMonitorStore((s) => s.setSpawnConfig);
  const setTopicsBundle = useMonitorStore((s) => s.setTopicsBundle);
  const setTrainingConfig = useMonitorStore((s) => s.setTrainingConfig);

  const [projects, setProjects] = useState<string[]>([]);
  const [projectDetails, setProjectDetails] = useState<ProjectSummary[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [gazeboHeadless, setGazeboHeadless] = useState(() => {
    try {
      return localStorage.getItem("quadrl.gazeboHeadless") !== "0";
    } catch {
      return true;
    }
  });
  const [guiAvailable, setGuiAvailable] = useState(true);
  const [resolvedDisplay, setResolvedDisplay] = useState<string | null>(null);
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus | null>(null);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<string | null>(null);
  const [tbStatus, setTbStatus] = useState<TensorBoardStatus | null>(null);

  const trainingActive = trainStatus?.state === "running" || trainStatus?.state === "starting";

  const refreshScalars = useCallback(
    async (name: string, runId: string | null) => {
      if (runId) {
        const sc = await api.getScalars(name, runId);
        setScalars(sc.series);
      } else {
        const sc = await api.getScalars(name);
        setScalars(sc.series);
      }
    },
    [setScalars]
  );

  const refreshProjectData = useCallback(
    async (name: string) => {
      const [exp, ckpt, runList, status, tb, ws, spawn, topics, trainCfg] = await Promise.all([
        api.getExports(name),
        api.listCheckpoints(name),
        api.listRuns(name),
        api.trainStatus(name),
        api.tbStatus(name),
        api.workspaceStatus(name),
        api.getSpawnConfig(name).catch(() => null),
        api.getTopics(name).catch(() => null),
        api.getTrainingConfig(name).catch(() => null),
      ]);
      setExports(exp);
      setWorkspaceStatus(ws);
      setCheckpoints(ckpt.checkpoints);
      setRuns(runList.runs);
      setTrainStatus(status);
      setTbStatus(tb);
      if (spawn) setSpawnConfig(spawn);
      if (topics) setTopicsBundle(topics);
      if (trainCfg) setTrainingConfig(trainCfg);

      const trainingNow = status.state === "running" || status.state === "starting";
      const activeRun =
        (trainingNow && status.run_id) || selectedRunId || runList.runs[0]?.run_id || null;
      if (activeRun && activeRun !== selectedRunId) {
        setSelectedRunId(activeRun);
      }
      await refreshScalars(name, activeRun);
    },
    [selectedRunId, setCheckpoints, setExports, setRuns, setSelectedRunId, setTrainStatus, refreshScalars, setSpawnConfig, setTopicsBundle, setTrainingConfig]
  );

  const refreshProjects = useCallback(async () => {
    const r = await api.listProjects();
    setProjects(r.projects);
    setProjectDetails(r.details ?? []);
    if (r.active) setProject(r.active);
  }, [setProject]);

  useEffect(() => {
    refreshProjects().catch(() => {});
    api
      .health()
      .then(() => {
        setConnected(true);
        log("Connected to Train Monitor API", { component: "api", level: "info" });
        api
          .displayStatus()
          .then((d) => {
            setGuiAvailable(d.gui_available);
            setResolvedDisplay(d.resolved_display ?? null);
            if (!d.gui_available) setGazeboHeadless(true);
          })
          .catch(() => setGuiAvailable(false));
      })
      .catch(() => {
        setConnected(false);
        setError("Backend unreachable — start train-monitor on port 8006");
      });
  }, [log, refreshProjects]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsTrainLogsUrl());
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data) as {
          entry?: WsLogPayload;
          status?: TrainStatus;
          workspace?: WorkspaceStatus;
        };
        if (data.entry) {
          const { timestamp, level, message, component } = data.entry;
          appendLog({
            timestamp,
            level: normalizeLogLevel(level),
            message,
            component: component ?? parseLogComponent(message),
          });
        }
        if (data.status) setTrainStatus(data.status);
        if (data.workspace) setWorkspaceStatus(data.workspace);
      };
    } catch {
      /* ignore */
    }
    return () => ws?.close();
  }, [appendLog, setTrainStatus]);

  useEffect(() => {
    if (!project) return;
    const id = window.setInterval(() => {
      refreshProjectData(project).catch(() => {});
    }, 5000);
    return () => window.clearInterval(id);
  }, [project, refreshProjectData]);

  useEffect(() => {
    if (!project) return;
    const ms = trainingActive ? 2000 : 8000;
    const runId = trainingActive && trainStatus?.run_id ? trainStatus.run_id : selectedRunId;
    const id = window.setInterval(() => {
      refreshScalars(project, runId).catch(() => {});
    }, ms);
    return () => window.clearInterval(id);
  }, [project, selectedRunId, trainingActive, trainStatus?.run_id, refreshScalars]);

  useEffect(() => {
    const onHash = () => {
      const page = window.location.hash.replace("#", "") as MonitorPageId;
      if (page === "spawn" || page === "topic" || page === "training" || page === "metric") {
        setActivePage(page);
      }
    };
    window.addEventListener("hashchange", onHash);
    onHash();
    return () => window.removeEventListener("hashchange", onHash);
  }, [setActivePage]);

  const loadProject = async (name: string) => {
    setError(null);
    setBusy(true);
    try {
      await api.loadProject(name);
      setProject(name);
      setSelectedCheckpoint(null);
      await refreshProjectData(name);
      log(`Loaded project ${name}`);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const selectRun = async (runId: string) => {
    if (!project) return;
    setSelectedRunId(runId);
    setError(null);
    try {
      await refreshScalars(project, runId);
    } catch (e) {
      setError(String(e));
    }
  };

  const startTraining = async () => {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      setScalars([]);
      const status = await api.trainStart(project, { dry_run: dryRun, gazebo_headless: gazeboHeadless });
      setTrainStatus(status);
      log("Training started");
      await refreshProjectData(project);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const stopTraining = async () => {
    if (!project) return;
    setBusy(true);
    try {
      setTrainStatus(await api.trainStop(project));
      log("Training stop requested");
      await refreshProjectData(project);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const resumeTraining = async () => {
    if (!project || !selectedCheckpoint) return;
    setBusy(true);
    try {
      setTrainStatus(
        await api.trainResume(project, selectedCheckpoint, { dry_run: dryRun, gazebo_headless: gazeboHeadless })
      );
      log(`Resuming from ${selectedCheckpoint}`);
      await refreshProjectData(project);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const startTb = async () => {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const tb = await api.tbStart(project, selectedRunId ?? undefined);
      setTbStatus(tb);
      if (tb.error) setError(tb.error);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const stopTb = async () => {
    if (!project) return;
    setBusy(true);
    try {
      setTbStatus(await api.tbStop(project));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app monitor-app">
      <header className="top-bar">
        <MenuBar projects={projects} projectDetails={projectDetails} active={project} onLoad={loadProject} />
        <PageNav active={activePage} onChange={setActivePage} />
      </header>

      {error && (
        <div className="error-bar" role="alert">
          {error}
          <button type="button" className="error-dismiss" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}

      <div className="monitor-main-split">
        <div className="monitor-page-body">
          {activePage !== "metric" && activePage !== "topic" && (
            <TestSpawnBar
              project={project}
              busy={busy}
              gazeboHeadless={gazeboHeadless}
              guiAvailable={guiAvailable}
              resolvedDisplay={resolvedDisplay}
              onBusy={setBusy}
              onError={setError}
              onGazeboHeadlessChange={(v) => {
                setGazeboHeadless(v);
                try {
                  localStorage.setItem("quadrl.gazeboHeadless", v ? "1" : "0");
                } catch {
                  /* ignore */
                }
              }}
            />
          )}
          {activePage === "spawn" && (
            <SpawnMonitorPage project={project} busy={busy} onBusy={setBusy} onError={setError} />
          )}
          {activePage === "topic" && (
            <TopicMonitorPage
              project={project}
              workspaceStatus={workspaceStatus}
              busy={busy}
              gazeboHeadless={gazeboHeadless}
              guiAvailable={guiAvailable}
              resolvedDisplay={resolvedDisplay}
              onBusy={setBusy}
              onError={setError}
              onWorkspaceDone={setWorkspaceStatus}
              onGazeboHeadlessChange={(v) => {
                setGazeboHeadless(v);
                try {
                  localStorage.setItem("quadrl.gazeboHeadless", v ? "1" : "0");
                } catch {
                  /* ignore */
                }
              }}
            />
          )}
          {activePage === "training" && (
            <TrainingMonitorPage project={project} trainStatus={trainStatus} busy={busy} onBusy={setBusy} onError={setError} />
          )}
          {activePage === "metric" && (
            <MetricMonitorPage
              project={project}
              exports={exports}
              trainStatus={trainStatus}
              workspaceStatus={workspaceStatus}
              checkpoints={checkpoints}
              runs={runs}
              scalars={scalars}
              selectedRunId={selectedRunId}
              selectedCheckpoint={selectedCheckpoint}
              tbStatus={tbStatus}
              dryRun={dryRun}
              gazeboHeadless={gazeboHeadless}
              guiAvailable={guiAvailable}
              resolvedDisplay={resolvedDisplay}
              busy={busy}
              trainingActive={trainingActive}
              onDryRunChange={setDryRun}
              onGazeboHeadlessChange={(v) => {
                setGazeboHeadless(v);
                try {
                  localStorage.setItem("quadrl.gazeboHeadless", v ? "1" : "0");
                } catch {
                  /* ignore */
                }
              }}
              onStart={startTraining}
              onStop={stopTraining}
              onResume={resumeTraining}
              onSelectCheckpoint={setSelectedCheckpoint}
              onSelectRun={selectRun}
              onOpenTb={startTb}
              onStopTb={stopTb}
            />
          )}
        </div>

        <ConsoleSplitter>
          <ConsolePanel />
        </ConsoleSplitter>
      </div>

      <StatusBar
        connected={connected}
        project={project}
        trainingActive={trainingActive}
        trainStatus={trainStatus}
      />
    </div>
  );
}
