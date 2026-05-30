import { create } from "zustand";
import type { PpoPlannerModel, ValidationResult } from "@ppo-model";

interface PlannerState {
  project: string | null;
  model: PpoPlannerModel | null;
  validation: ValidationResult | null;
  logs: string[];
  setProject: (p: string | null) => void;
  setModel: (m: PpoPlannerModel | null) => void;
  setValidation: (v: ValidationResult | null) => void;
  log: (msg: string) => void;
}

export const usePlannerStore = create<PlannerState>((set) => ({
  project: null,
  model: null,
  validation: null,
  logs: [],
  setProject: (p) => set({ project: p }),
  setModel: (m) => set({ model: m }),
  setValidation: (v) => set({ validation: v }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
}));
