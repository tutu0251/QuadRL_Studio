import { create } from "zustand";
import type { CheckpointInfo, ExportBundle, LogEntry, LogLevel, RunInfo, ScalarSeries, TrainStatus } from "../types";
import { createLogEntry, nextLogId } from "../utils/logUtils";

const MAX_LOGS = 500;

type MonitorState = {
  project: string | null;
  exports: ExportBundle | null;
  checkpoints: CheckpointInfo[];
  runs: RunInfo[];
  trainStatus: TrainStatus | null;
  scalars: ScalarSeries[];
  selectedRunId: string | null;
  selectedExportPath: string | null;
  exportPreview: string | null;
  logs: LogEntry[];
  setProject: (name: string | null) => void;
  setExports: (bundle: ExportBundle | null) => void;
  setCheckpoints: (items: CheckpointInfo[]) => void;
  setRuns: (items: RunInfo[]) => void;
  setTrainStatus: (status: TrainStatus | null) => void;
  setScalars: (items: ScalarSeries[]) => void;
  setSelectedRunId: (id: string | null) => void;
  setSelectedExportPath: (path: string | null) => void;
  setExportPreview: (text: string | null) => void;
  log: (message: string, options?: { level?: LogLevel; component?: string }) => void;
  appendLog: (entry: Omit<LogEntry, "id">) => void;
  clearLogs: () => void;
};

function trimLogs(logs: LogEntry[]): LogEntry[] {
  return logs.length > MAX_LOGS ? logs.slice(-MAX_LOGS) : logs;
}

export const useMonitorStore = create<MonitorState>((set) => ({
  project: null,
  exports: null,
  checkpoints: [],
  runs: [],
  trainStatus: null,
  scalars: [],
  selectedRunId: null,
  selectedExportPath: null,
  exportPreview: null,
  logs: [],
  setProject: (project) => set({ project }),
  setExports: (exports) => set({ exports }),
  setCheckpoints: (checkpoints) => set({ checkpoints }),
  setRuns: (runs) => set({ runs }),
  setTrainStatus: (trainStatus) => set({ trainStatus }),
  setScalars: (scalars) => set({ scalars }),
  setSelectedRunId: (selectedRunId) => set({ selectedRunId }),
  setSelectedExportPath: (selectedExportPath) => set({ selectedExportPath }),
  setExportPreview: (exportPreview) => set({ exportPreview }),
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
