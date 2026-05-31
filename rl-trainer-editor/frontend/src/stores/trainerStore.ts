import { create } from "zustand";
import type { RlTrainerModel, ValidationResult } from "@rl-trainer-model";

interface TrainerState {
  project: string | null;
  model: RlTrainerModel | null;
  validation: ValidationResult | null;
  activeTab: string;
  logs: string[];
  setProject: (p: string | null) => void;
  setModel: (m: RlTrainerModel | null) => void;
  setValidation: (v: ValidationResult | null) => void;
  setActiveTab: (tab: string) => void;
  log: (msg: string) => void;
}

export const useTrainerStore = create<TrainerState>((set) => ({
  project: null,
  model: null,
  validation: null,
  activeTab: "curriculum",
  logs: [],
  setProject: (p) => set({ project: p }),
  setModel: (m) => set({ model: m }),
  setValidation: (v) => set({ validation: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
}));
