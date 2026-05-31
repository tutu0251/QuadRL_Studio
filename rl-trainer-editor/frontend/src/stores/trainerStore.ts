import { create } from "zustand";
import type { RlTrainerModel, ValidationResult } from "@rl-trainer-model";

interface TrainerState {
  project: string | null;
  model: RlTrainerModel | null;
  validation: ValidationResult | null;
  activeTab: string;
  selectedStageId: string | null;
  selectedGaitTypeId: string | null;
  logs: string[];
  setProject: (p: string | null) => void;
  setModel: (m: RlTrainerModel | null) => void;
  setValidation: (v: ValidationResult | null) => void;
  setActiveTab: (tab: string) => void;
  setSelectedStageId: (id: string | null) => void;
  setSelectedGaitTypeId: (id: string | null) => void;
  log: (msg: string) => void;
}

export const useTrainerStore = create<TrainerState>((set) => ({
  project: null,
  model: null,
  validation: null,
  activeTab: "curriculum",
  selectedStageId: null,
  selectedGaitTypeId: null,
  logs: [],
  setProject: (p) => set({ project: p }),
  setModel: (m) => set({ model: m }),
  setValidation: (v) => set({ validation: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedStageId: (id) => set({ selectedStageId: id }),
  setSelectedGaitTypeId: (id) => set({ selectedGaitTypeId: id }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
}));
