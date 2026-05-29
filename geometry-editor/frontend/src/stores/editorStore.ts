import { create } from "zustand";
import type {
  GizmoMode,
  GizmoTarget,
  MeasurementResult,
  RobotModel,
  Selection,
} from "@robot-model";

interface EditorState {
  project: string | null;
  model: RobotModel | null;
  selection: Selection;
  gizmoMode: GizmoMode;
  gizmoTarget: GizmoTarget;
  showLinkFrames: boolean;
  showJointFrames: boolean;
  showJointAxes: boolean;
  measurement: MeasurementResult | null;
  logs: string[];
  setProject: (p: string | null) => void;
  setModel: (m: RobotModel | null) => void;
  setSelection: (s: Selection) => void;
  setGizmoMode: (m: GizmoMode) => void;
  setGizmoTarget: (t: GizmoTarget) => void;
  toggleLinkFrames: () => void;
  toggleJointFrames: () => void;
  toggleJointAxes: () => void;
  setMeasurement: (m: MeasurementResult | null) => void;
  log: (msg: string) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  project: null,
  model: null,
  selection: null,
  gizmoMode: "translate",
  gizmoTarget: "link",
  showLinkFrames: true,
  showJointFrames: true,
  showJointAxes: true,
  measurement: null,
  logs: [],
  setProject: (project) => set({ project }),
  setModel: (model) => set({ model }),
  setSelection: (selection) => {
    const next: Selection = selection;
    if (next?.kind === "link") set({ selection: next, gizmoTarget: "link" });
    else if (next?.kind === "joint") set({ selection: next, gizmoTarget: "joint" });
    else if (next?.kind === "shape") set({ selection: next, gizmoTarget: "shape" });
    else set({ selection: next });
  },
  setGizmoMode: (gizmoMode) => set({ gizmoMode }),
  setGizmoTarget: (gizmoTarget) => set({ gizmoTarget }),
  toggleLinkFrames: () => set((s) => ({ showLinkFrames: !s.showLinkFrames })),
  toggleJointFrames: () => set((s) => ({ showJointFrames: !s.showJointFrames })),
  toggleJointAxes: () => set((s) => ({ showJointAxes: !s.showJointAxes })),
  setMeasurement: (measurement) => set({ measurement }),
  log: (msg) => set((s) => ({ logs: [...s.logs.slice(-200), msg] })),
}));
