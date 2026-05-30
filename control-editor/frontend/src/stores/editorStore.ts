import { create } from "zustand";
import type { ControlModel, Selection } from "@control-model";

interface EditorState {
  project: string | null;
  model: ControlModel | null;
  selection: Selection;
  logs: string[];
  consoleFocus: number;
  setProject: (p: string | null) => void;
  setModel: (m: ControlModel | null) => void;
  setSelection: (s: Selection) => void;
  log: (msg: string) => void;
  focusConsole: () => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  project: null,
  model: null,
  selection: null,
  logs: [],
  consoleFocus: 0,
  setProject: (p) => set({ project: p }),
  setModel: (m) => set({ model: m }),
  setSelection: (s) => set({ selection: s }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
  focusConsole: () => set((s) => ({ consoleFocus: s.consoleFocus + 1 })),
}));
