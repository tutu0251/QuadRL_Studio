import { create } from "zustand";
import type {
  CheckpointInfo,
  ExportBundle,
  LogEntry,
  LogLevel,
  MonitorPageId,
  RunInfo,
  ScalarSeries,
  SpawnConfig,
  TopicsBundle,
  TrainStatus,
  TrainingConfig,
} from "../types";
import { createLogEntry, nextLogId } from "../utils/logUtils";

const MAX_LOGS = 500;

type MonitorState = {
  project: string | null;
  activePage: MonitorPageId;
  consoleFilter: string | null;
  exports: ExportBundle | null;
  checkpoints: CheckpointInfo[];
  runs: RunInfo[];
  trainStatus: TrainStatus | null;
  scalars: ScalarSeries[];
  selectedRunId: string | null;
  selectedStageLogdir: string | null;
  selectedExportPath: string | null;
  exportPreview: string | null;
  spawnConfig: SpawnConfig | null;
  topicsBundle: TopicsBundle | null;
  trainingConfig: TrainingConfig | null;
  logs: LogEntry[];
  setProject: (name: string | null) => void;
  setActivePage: (page: MonitorPageId) => void;
  setConsoleFilter: (filter: string | null) => void;
  setExports: (bundle: ExportBundle | null) => void;
  setCheckpoints: (items: CheckpointInfo[]) => void;
  setRuns: (items: RunInfo[]) => void;
  setTrainStatus: (status: TrainStatus | null) => void;
  setScalars: (items: ScalarSeries[]) => void;
  setSelectedRunId: (id: string | null) => void;
  setSelectedStageLogdir: (logdir: string | null) => void;
  setSelectedExportPath: (path: string | null) => void;
  setExportPreview: (text: string | null) => void;
  setSpawnConfig: (cfg: SpawnConfig | null) => void;
  setTopicsBundle: (bundle: TopicsBundle | null) => void;
  setTrainingConfig: (cfg: TrainingConfig | null) => void;
  log: (message: string, options?: { level?: LogLevel; component?: string }) => void;
  appendLog: (entry: Omit<LogEntry, "id">) => void;
  clearLogs: () => void;
};

function trimLogs(logs: LogEntry[]): LogEntry[] {
  return logs.length > MAX_LOGS ? logs.slice(-MAX_LOGS) : logs;
}

function loadActivePage(): MonitorPageId {
  try {
    const hash = window.location.hash.replace("#", "") as MonitorPageId;
    if (hash === "spawn" || hash === "topic" || hash === "training" || hash === "metric") return hash;
    const stored = localStorage.getItem("quadrl.trainMonitor.page") as MonitorPageId;
    if (stored === "spawn" || stored === "topic" || stored === "training" || stored === "metric") return stored;
  } catch {
    /* ignore */
  }
  return "spawn";
}

export const useMonitorStore = create<MonitorState>((set) => ({
  project: null,
  activePage: loadActivePage(),
  consoleFilter: null,
  exports: null,
  checkpoints: [],
  runs: [],
  trainStatus: null,
  scalars: [],
  selectedRunId: null,
  selectedStageLogdir: null,
  selectedExportPath: null,
  exportPreview: null,
  spawnConfig: null,
  topicsBundle: null,
  trainingConfig: null,
  logs: [],
  setProject: (project) => set({ project }),
  setActivePage: (activePage) => {
    try {
      localStorage.setItem("quadrl.trainMonitor.page", activePage);
      window.location.hash = activePage;
    } catch {
      /* ignore */
    }
    set({ activePage });
  },
  setConsoleFilter: (consoleFilter) => set({ consoleFilter }),
  setExports: (exports) => set({ exports }),
  setCheckpoints: (checkpoints) => set({ checkpoints }),
  setRuns: (runs) => set({ runs }),
  setTrainStatus: (trainStatus) => set({ trainStatus }),
  setScalars: (scalars) => set({ scalars }),
  setSelectedRunId: (selectedRunId) => set({ selectedRunId }),
  setSelectedStageLogdir: (selectedStageLogdir) => set({ selectedStageLogdir }),
  setSelectedExportPath: (selectedExportPath) => set({ selectedExportPath }),
  setExportPreview: (exportPreview) => set({ exportPreview }),
  setSpawnConfig: (spawnConfig) => set({ spawnConfig }),
  setTopicsBundle: (topicsBundle) => set({ topicsBundle }),
  setTrainingConfig: (trainingConfig) => set({ trainingConfig }),
  appendLog: (entry) =>
    set((s) => ({
      logs: trimLogs([...s.logs, { ...entry, id: nextLogId() }]),
    })),
  log: (message, options) =>
    set((s) => ({
      logs: trimLogs([
        ...s.logs,
        { id: nextLogId(), ...createLogEntry(message, { component: options?.component ?? "ui", ...options }) },
      ]),
    })),
  clearLogs: () => set({ logs: [] }),
}));
