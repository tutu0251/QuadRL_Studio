import { useCallback, useEffect, useState } from "react";
import { api, wsTrainLogsUrl } from "./api/client";
import { CheckpointsPanel } from "./features/checkpoints/CheckpointsPanel";
import { ConsolePanel } from "./features/console/ConsolePanel";
import { ExportsPanel } from "./features/exports/ExportsPanel";
import { MenuBar } from "./features/menu/MenuBar";
import { RunsPanel } from "./features/runs/RunsPanel";
import { StatusBar } from "./features/status/StatusBar";
import { TensorBoardPanel } from "./features/tensorboard/TensorBoardPanel";
import { TrainingPanel } from "./features/training/TrainingPanel";
import { useMonitorStore } from "./stores/monitorStore";
import type { ProjectSummary, TensorBoardStatus } from "./types";

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
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<string | null>(null);
  const [tbStatus, setTbStatus] = useState<TensorBoardStatus | null>(null);

  const ensureTensorBoard = useCallback(
    async (name: string, runId: string | null, runList: typeof runs) => {
      const run = runList.find((r) => r.run_id === runId);
      const hasEvents = run?.stages.some((s) => s.has_events) ?? false;
      if (runId && !hasEvents) {
        return;
      }
      try {
        const tb = await api.tbStart(name, runId ?? undefined);
        setTbStatus(tb);
        if (tb.error) {
          setError(tb.error);
        }
      } catch (e) {
        setError(String(e));
      }
    },
    []
  );

  const refreshProjectData = useCallback(
    async (name: string) => {
      const [exp, ckpt, runList, status, tb] = await Promise.all([
        api.getExports(name),
        api.listCheckpoints(name),
        api.listRuns(name),
        api.trainStatus(name),
        api.tbStatus(name),
      ]);
      setExports(exp);
      setCheckpoints(ckpt.checkpoints);
      setRuns(runList.runs);
      setTrainStatus(status);
      setTbStatus(tb);

      const activeRun = selectedRunId ?? runList.runs[0]?.run_id ?? null;
      if (!selectedRunId && activeRun) {
        setSelectedRunId(activeRun);
      }
      if (activeRun) {
        const sc = await api.getScalars(name, activeRun);
        setScalars(sc.series);
        if (!tb.running) {
          await ensureTensorBoard(name, activeRun, runList.runs);
        }
      } else {
        const sc = await api.getScalars(name);
        setScalars(sc.series);
      }
    },
    [selectedRunId, setCheckpoints, setExports, setRuns, setScalars, setSelectedRunId, setTrainStatus, ensureTensorBoard]
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
        log("Connected to Train Monitor API");
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
        const data = JSON.parse(ev.data);
        if (data.entry) log(`[${data.entry.level}] ${data.entry.message}`);
        if (data.status) setTrainStatus(data.status);
      };
    } catch {
      /* ignore */
    }
    return () => ws?.close();
  }, [log, setTrainStatus]);

  useEffect(() => {
    if (!project) return;
    const id = window.setInterval(() => {
      refreshProjectData(project).catch(() => {});
    }, 5000);
    return () => window.clearInterval(id);
  }, [project, refreshProjectData]);

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
      const sc = await api.getScalars(project, runId);
      setScalars(sc.series);
      await ensureTensorBoard(project, runId, runs);
    } catch (e) {
      setError(String(e));
    }
  };

  const startTraining = async () => {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const status = await api.trainStart(project, { dry_run: dryRun });
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
      const status = await api.trainResume(project, selectedCheckpoint, dryRun);
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
      <div className="top-bar">
        <MenuBar
          projects={projects}
          projectDetails={projectDetails}
          active={project}
          onLoad={loadProject}
        />
      </div>

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
          <TrainingPanel
            project={project}
            status={trainStatus}
            ready={exports?.ready_for_training ?? false}
            selectedCheckpoint={selectedCheckpoint}
            dryRun={dryRun}
            onDryRunChange={setDryRun}
            onStart={startTraining}
            onStop={stopTraining}
            onResume={resumeTraining}
            busy={busy}
          />
          <CheckpointsPanel
            checkpoints={checkpoints}
            selected={selectedCheckpoint}
            onSelect={setSelectedCheckpoint}
          />
          <RunsPanel runs={runs} selectedRunId={selectedRunId} onSelect={selectRun} />
        </aside>

        <main className="main-col">
          <ExportsPanel
            bundle={exports}
            selectedPath={selectedExportPath}
            preview={exportPreview}
            onSelect={selectExport}
          />
          <TensorBoardPanel
            scalars={scalars}
            tbStatus={tbStatus}
            onStartTb={startTb}
            onStopTb={stopTb}
            busy={busy}
          />
        </main>
      </div>

      <div className="bottom-dock">
        <ConsolePanel />
      </div>

      <StatusBar connected={connected} project={project} />
    </div>
  );
}
