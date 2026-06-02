import { create } from "zustand";
import type { CheckpointInfo, ExportBundle, LogEntry, LogLevel, RunInfo, ScalarSeries, TrainStatus } from "../types";

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
  log: (message: string) => void;
  clearLogs: () => void;
};

const BRACKET_TAG = /^\[([^\]]+)\]\s*/;

function parseLogLine(message: string): { level: LogLevel; component: string | null; text: string } {
  let rest = message.trim();
  const tags: string[] = [];
  while (true) {
    const m = rest.match(BRACKET_TAG);
    if (!m) break;
    tags.push(m[1].trim());
    rest = rest.slice(m[0].length).trimStart();
  }

  const norm = tags.map((t) => t.toLowerCase());
  let level: LogLevel = "info";
  for (const t of norm) {
    if (t === "debug" || t === "info" || t === "warn" || t === "error") {
      level = t;
      break;
    }
    if (t === "warning") {
      level = "warn";
      break;
    }
  }

  const component =
    norm.find((t) => t === "train" || t === "gazebo" || t === "ros" || t === "sim") ?? null;

  return { level, component, text: rest || message.trim() };
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
  log: (message) =>
    set((s) => ({
      logs: (() => {
        const ts = new Date().toLocaleTimeString();
        const parsed = parseLogLine(message);
        const entry: LogEntry = {
          ts,
          level: parsed.level,
          component: parsed.component,
          message: parsed.text,
          rawLine: `[${ts}] ${message}`,
        };
        return [...s.logs.slice(-400), entry];
      })(),
    })),
  clearLogs: () => set({ logs: [] }),
}));
