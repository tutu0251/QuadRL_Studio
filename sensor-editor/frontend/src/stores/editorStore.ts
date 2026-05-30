import { create } from "zustand";
import type { Selection, SensorModel } from "@sensor-model";

interface EditorState {
  project: string | null;
  model: SensorModel | null;
  selection: Selection;
  logs: string[];
  setProject: (p: string | null) => void;
  setModel: (m: SensorModel | null) => void;
  setSelection: (s: Selection) => void;
  log: (msg: string) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  project: null,
  model: null,
  selection: null,
  logs: [],
  setProject: (p) => set({ project: p }),
  setModel: (m) => set({ model: m }),
  setSelection: (s) => set({ selection: s }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
}));
