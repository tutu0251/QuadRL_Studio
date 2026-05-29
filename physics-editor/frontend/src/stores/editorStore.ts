import { create } from "zustand";
import type { RobotModel, Selection, Vec3 } from "@robot-model";

interface EditorState {
  project: string | null;
  model: RobotModel | null;
  selection: Selection;
  showCom: boolean;
  showInertiaAxes: boolean;
  showWholeCom: boolean;
  wholeCom: Vec3 | null;
  logs: string[];
  setProject: (p: string | null) => void;
  setModel: (m: RobotModel | null) => void;
  setSelection: (s: Selection) => void;
  toggleCom: () => void;
  toggleInertiaAxes: () => void;
  toggleWholeCom: () => void;
  setWholeCom: (c: Vec3 | null) => void;
  log: (msg: string) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  project: null,
  model: null,
  selection: null,
  showCom: true,
  showInertiaAxes: true,
  showWholeCom: true,
  wholeCom: null,
  logs: [],
  setProject: (p) => set({ project: p }),
  setModel: (m) => set({ model: m }),
  setSelection: (s) => set({ selection: s }),
  toggleCom: () => set((s) => ({ showCom: !s.showCom })),
  toggleInertiaAxes: () => set((s) => ({ showInertiaAxes: !s.showInertiaAxes })),
  toggleWholeCom: () => set((s) => ({ showWholeCom: !s.showWholeCom })),
  setWholeCom: (c) => set({ wholeCom: c }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
}));
