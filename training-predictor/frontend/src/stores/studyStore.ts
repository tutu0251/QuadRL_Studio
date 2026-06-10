import { create } from "zustand";
import type { Health, LogEntry, StartRequest, StudyStatus, TrialRow } from "../api/types";

/** Sensible defaults mirroring the backend's StartTuningRequest field defaults. */
export function defaultForm(project = ""): StartRequest {
  return {
    project,
    n_trials: 20,
    advisor_every_n: 5,
    trial_timesteps: 30_000,
    gazebo_headless: true,
    max_stages: null,
    monitor_base_url: null,
    mock_objective: false,
    include_hyperparams: true,
    include_reward_weights: true,
    include_reward_params: true,
    trial_timeout: null,
  };
}

interface StudyState {
  // connection / catalog
  connected: boolean;
  health: Health | null;
  projects: string[];
  error: string | null;

  // setup form
  form: StartRequest;

  // active run
  taskId: string | null;
  status: StudyStatus | null;
  trials: TrialRow[];
  logs: LogEntry[];
  applyResult: string | null;
  applying: boolean;

  setConnected: (v: boolean) => void;
  setHealth: (h: Health | null) => void;
  setProjects: (p: string[]) => void;
  setError: (e: string | null) => void;

  setProject: (p: string) => void;
  patchForm: (patch: Partial<StartRequest>) => void;

  beginRun: (taskId: string) => void;
  setStatus: (s: StudyStatus) => void;
  setTrials: (t: TrialRow[]) => void;
  appendLog: (e: LogEntry) => void;
  setApplyResult: (s: string | null) => void;
  setApplying: (v: boolean) => void;
}

/** Derived: is a study currently in flight? */
export const isRunning = (s: StudyState): boolean =>
  s.taskId !== null && (s.status === null || s.status.status === "running" || s.status.status === "pending");

export const useStudyStore = create<StudyState>((set) => ({
  connected: false,
  health: null,
  projects: [],
  error: null,

  form: defaultForm(),

  taskId: null,
  status: null,
  trials: [],
  logs: [],
  applyResult: null,
  applying: false,

  setConnected: (v) => set({ connected: v }),
  setHealth: (h) => set({ health: h }),
  setProjects: (p) => set({ projects: p }),
  setError: (e) => set({ error: e }),

  setProject: (p) => set((s) => ({ form: { ...s.form, project: p } })),
  patchForm: (patch) => set((s) => ({ form: { ...s.form, ...patch } })),

  beginRun: (taskId) =>
    set({ taskId, status: null, trials: [], logs: [], applyResult: null }),
  setStatus: (status) => set({ status }),
  setTrials: (trials) => set({ trials }),
  appendLog: (e) => set((s) => ({ logs: [...s.logs.slice(-500), e] })),
  setApplyResult: (s2) => set({ applyResult: s2 }),
  setApplying: (v) => set({ applying: v }),
}));
