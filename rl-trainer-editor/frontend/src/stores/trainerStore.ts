import { create } from "zustand";
import type { RlTrainerModel, ValidationResult } from "@rl-trainer-model";

interface TrainingStatus {
  running: boolean;
  project: string | null;
  taskId: string | null;
  pid: number | null;
}

interface TrainerState {
  project: string | null;
  model: RlTrainerModel | null;
  validation: ValidationResult | null;
  activeTab: string;
  training: TrainingStatus;
  logs: string[];
  setProject: (p: string | null) => void;
  setModel: (m: RlTrainerModel | null) => void;
  setValidation: (v: ValidationResult | null) => void;
  setActiveTab: (tab: string) => void;
  setTraining: (t: TrainingStatus) => void;
  log: (msg: string) => void;
}

export const useTrainerStore = create<TrainerState>((set) => ({
  project: null,
  model: null,
  validation: null,
  activeTab: "presets",
  training: { running: false, project: null, taskId: null, pid: null },
  logs: [],
  setProject: (p) => set({ project: p }),
  setModel: (m) => set({ model: m }),
  setValidation: (v) => set({ validation: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setTraining: (t) => set({ training: t }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
}));
