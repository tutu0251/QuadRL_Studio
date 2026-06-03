import { useCallback, useEffect, useState } from "react";
import { api, wsTrainLogsUrl } from "./api/client";
import { CheckpointsPanel } from "./features/checkpoints/CheckpointsPanel";
import { ConsolePanel } from "./features/console/ConsolePanel";
import { ExportsPanel } from "./features/exports/ExportsPanel";
import { MenuBar } from "./features/menu/MenuBar";
import { MetricsPanel } from "./features/tensorboard/MetricsPanel";
import { RunsPanel } from "./features/runs/RunsPanel";
import { StatusBar } from "./features/status/StatusBar";
import { SystemResourcesPanel } from "./features/system/SystemResourcesPanel";
import { TrainingPanel } from "./features/training/TrainingPanel";
import { WorkspacePanel } from "./features/workspace/WorkspacePanel";
import { useMonitorStore } from "./stores/monitorStore";
import type { ProjectSummary, TensorBoardStatus, TrainStatus, WorkspaceStatus, WsLogPayload } from "./types";
import { normalizeLogLevel, parseLogComponent } from "./utils/logUtils";

export default function App() {
  const project = useMonitorStore((s) => s.project);
  const exports = useMonitorStore((s) => s.exports);
  const checkpoints = useMonitorStore((s) => s.checkpoints);
  const runs = useMonitorStore((s) => s.runs);
  const trainStatus = useMonitorStore((s) => s.trainStatus);
  const scalars = useMonitorStore((s) => s.scalars);
  const selectedRunId = useMonitorStore((s) => s.selectedRunId);
  const selectedExportPath = useMonitorStore((s) => s.selectedExportPath);
  const exportPreview = useMonitorStore((s) => s.exportPreview);
  const log = useMonitorStore((s) => s.log);
  const appendLog = useMonitorStore((s) => s.appendLog);
  const setProject = useMonitorStore((s) => s.setProject);
  const setExports = useMonitorStore((s) => s.setExports);
  const setCheckpoints = useMonitorStore((s) => s.setCheckpoints);
  const setRuns = useMonitorStore((s) => s.setRuns);
  const setTrainStatus = useMonitorStore((s) => s.setTrainStatus);
  const setScalars = useMonitorStore((s) => s.setScalars);
  const setSelectedRunId = useMonitorStore((s) => s.setSelectedRunId);
  const setSelectedExportPath = useMonitorStore((s) => s.setSelectedExportPath);
  const setExportPreview = useMonitorStore((s) => s.setExportPreview);

  const [projects, setProjects] = useState<string[]>([]);
  const [projectDetails, setProjectDetails] = useState<ProjectSummary[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [gazeboHeadless, setGazeboHeadless] = useState(() => {
    try {
      const v = localStorage.getItem("quadrl.gazeboHeadless");
      return v !== "0";
    } catch {
      return true;
    }
  });
  const [guiAvailable, setGuiAvailable] = useState(true);
  const [resolvedDisplay, setResolvedDisplay] = useState<string | null>(null);
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus | null>(null);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<string | null>(null);
  const [tbStatus, setTbStatus] = useState<TensorBoardStatus | null>(null);

  const trainingActive =
    trainStatus?.state === "running" || trainStatus?.state === "starting";

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
      const [exp, ckpt, runList, status, tb, ws] = await Promise.all([
        api.getExports(name),
        api.listCheckpoints(name),
        api.listRuns(name),
        api.trainStatus(name),
        api.tbStatus(name),
        api.workspaceStatus(name),
      ]);
      setExports(exp);
      setWorkspaceStatus(ws);
      setCheckpoints(ckpt.checkpoints);
      setRuns(runList.runs);
      setTrainStatus(status);
      setTbStatus(tb);

      const trainingNow = status.state === "running" || status.state === "starting";
      const activeRun =
        (trainingNow && status.run_id) ||
        selectedRunId ||
        runList.runs[0]?.run_id ||
        null;
      if (activeRun && activeRun !== selectedRunId) {
        setSelectedRunId(activeRun);
      }
      await refreshScalars(name, activeRun);
    },
    [
      selectedRunId,
      setCheckpoints,
      setExports,
      setRuns,
      setSelectedRunId,
      setTrainStatus,
      refreshScalars,
    ]
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
          .catch(() => {
            setGuiAvailable(false);
          });
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
    const runId =
      trainingActive && trainStatus?.run_id ? trainStatus.run_id : selectedRunId;
    const id = window.setInterval(() => {
      refreshScalars(project, runId).catch(() => {});
    }, ms);
    return () => window.clearInterval(id);
  }, [project, selectedRunId, trainingActive, trainStatus?.run_id, refreshScalars]);

  useEffect(() => {
    if (!project || !trainingActive || !trainStatus?.run_id) return;
    if (trainStatus.run_id === selectedRunId) return;
    setSelectedRunId(trainStatus.run_id);
    refreshScalars(project, trainStatus.run_id).catch(() => {});
  }, [
    project,
    trainingActive,
    trainStatus?.run_id,
    selectedRunId,
    setSelectedRunId,
    refreshScalars,
  ]);

  const loadProject = async (name: string) => {
    setError(null);
    setBusy(true);
    try {
      await api.loadProject(name);
      setProject(name);
      setSelectedCheckpoint(null);
      setSelectedExportPath(null);
      setExportPreview(null);
      await refreshProjectData(name);
      log(`Loaded project ${name}`);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const selectExport = async (path: string) => {
    if (!project) return;
    setSelectedExportPath(path);
    try {
      const r = await api.getExportContent(project, path);
      setExportPreview(r.content);
    } catch (e) {
      setExportPreview(String(e));
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
      const status = await api.trainStart(project, {
        dry_run: dryRun,
        gazebo_headless: gazeboHeadless,
      });
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
      const status = await api.trainStop(project);
      setTrainStatus(status);
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
      const status = await api.trainResume(project, selectedCheckpoint, {
        dry_run: dryRun,
        gazebo_headless: gazeboHeadless,
      });
      setTrainStatus(status);
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

  const runWorkspace = async (fn: () => Promise<WorkspaceStatus>) => {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const ws = await fn();
      setWorkspaceStatus(ws);
      if (ws.error) setError(ws.error);
      await refreshProjectData(project);
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
      const tb = await api.tbStop(project);
      setTbStatus(tb);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app monitor-app">
      <header className="top-bar">
        <MenuBar
          projects={projects}
          projectDetails={projectDetails}
          active={project}
          onLoad={loadProject}
        />
      </header>

      {error && (
        <div className="error-bar" role="alert">
          {error}
          <button type="button" className="error-dismiss" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}

      <div className="monitor-body">
        <aside className="side-col">
          <WorkspacePanel
            project={project}
            status={workspaceStatus}
            busy={busy}
            onRefresh={() => project && api.workspaceStatus(project).then(setWorkspaceStatus)}
            onGenerate={() => runWorkspace(() => api.workspaceGenerate(project!))}
            onBuild={(clean) => runWorkspace(() => api.workspaceBuild(project!, { clean }))}
            onValidateExports={() => runWorkspace(() => api.workspaceValidateExports(project!))}
            onValidate={({ staticOnly, skipRuntime }) =>
              runWorkspace(() =>
                api.workspaceValidate(project!, {
                  static_only: staticOnly,
                  skip_runtime: skipRuntime,
                })
              )
            }
            onSetup={({ staticOnly, skipRuntime }) =>
              runWorkspace(() =>
                api.workspaceSetup(project!, { static_only: staticOnly, skip_runtime: skipRuntime })
              )
            }
          />
          <TrainingPanel
            project={project}
            status={trainStatus}
            ready={exports?.ready_for_training ?? false}
            selectedCheckpoint={selectedCheckpoint}
            dryRun={dryRun}
            gazeboHeadless={gazeboHeadless}
            guiAvailable={guiAvailable}
            resolvedDisplay={resolvedDisplay}
            recommendedSim={workspaceStatus?.recommended_sim_backend ?? exports?.recommended_sim_backend ?? "unavailable"}
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
            busy={busy}
          />
          <SystemResourcesPanel />
          <CheckpointsPanel
            checkpoints={checkpoints}
            selected={selectedCheckpoint}
            onSelect={setSelectedCheckpoint}
          />
          <RunsPanel runs={runs} selectedRunId={selectedRunId} onSelect={selectRun} />
        </aside>

        <main className="main-col">
          <MetricsPanel
            project={project}
            scalars={scalars}
            tbStatus={tbStatus}
            trainingActive={trainingActive}
            onOpenTb={startTb}
            onStopTb={stopTb}
            busy={busy}
          />
          <ExportsPanel
            bundle={exports}
            selectedPath={selectedExportPath}
            preview={exportPreview}
            onSelect={selectExport}
          />
        </main>
      </div>

      <div className="bottom-dock">
        <ConsolePanel />
      </div>

      <StatusBar connected={connected} project={project} trainingActive={trainingActive} />
    </div>
  );
}
