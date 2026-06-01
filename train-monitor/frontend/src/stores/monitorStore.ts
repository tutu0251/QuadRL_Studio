import { create } from "zustand";
import type { CheckpointInfo, ExportBundle, RunInfo, ScalarSeries, TrainStatus } from "../types";

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
  logs: string[];
  setProject: (name: string | null) => void;
  setExports: (bundle: ExportBundle | null) => void;
  setCheckpoints: (items: CheckpointInfo[]) => void;
  setRuns: (items: RunInfo[]) => void;
  setTrainStatus: (status: TrainStatus | null) => void;
  setScalars: (items: ScalarSeries[]) => void;
  setSelectedRunId: (id: string | null) => void;
  setSelectedExportPath: (path: string | null) => void;
  setExportPreview: (text: string | null) => void;
  log: (message: string) => void;
  clearLogs: () => void;
};

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
  log: (message) =>
    set((s) => ({
      logs: [...s.logs.slice(-400), `[${new Date().toLocaleTimeString()}] ${message}`],
    })),
  clearLogs: () => set({ logs: [] }),
}));
