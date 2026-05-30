import type {
  CurriculumConfig,
  CurriculumInfo,
  MachineProfile,
  ParallelConfig,
  PpoHyperparams,
  PresetInfo,
  RlTrainerModel,
  RewardTerm,
  TerminationConfig,
  ValidationResult,
} from "@rl-trainer-model";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8005";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<T>;
}

export const wsLogsUrl = () => {
  const u = new URL(BASE);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  return `${u.origin}/ws/logs`;
};

export type HyperparamsPatch = Partial<PpoHyperparams> & { useRecommended?: boolean };
export type ParallelPatch = Partial<ParallelConfig> & { useRecommended?: boolean };
export type ModelPatch = {
  selectedPresetId?: string | null;
  useRecommended?: boolean;
  rewardTerms?: RewardTerm[];
  termination?: TerminationConfig;
  curriculum?: CurriculumConfig;
  customParams?: Record<string, string | number | boolean>;
};

export const api = {
  health: () => req<{ status: string }>("/api/health"),
  machine: () => req<MachineProfile>("/api/machine"),
  presets: () => req<{ presets: PresetInfo[] }>("/api/presets"),
  curricula: () => req<{ curricula: CurriculumInfo[] }>("/api/curricula"),
  listProjects: () =>
    req<{
      projects: string[];
      active: string | null;
      details: { name: string; hasSensor: boolean; hasTrainer: boolean }[];
    }>("/api/projects"),
  loadProject: (name: string) =>
    req<{ project: string; model: RlTrainerModel; hasTrainer: boolean }>(
      `/api/projects/${name}/load`,
      { method: "POST" }
    ),
  bootstrap: (name: string) =>
    req<{ project: string; model: RlTrainerModel }>(`/api/projects/${name}/bootstrap`, {
      method: "POST",
    }),
  getModel: (name: string) => req<RlTrainerModel>(`/api/projects/${name}/model`),
  patchModel: (name: string, body: ModelPatch) =>
    req<RlTrainerModel>(`/api/projects/${name}/model`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  patchHyperparams: (name: string, body: HyperparamsPatch) =>
    req<RlTrainerModel>(`/api/projects/${name}/hyperparams`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  patchParallel: (name: string, body: ParallelPatch) =>
    req<RlTrainerModel>(`/api/projects/${name}/parallel`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  applyPreset: (name: string, presetId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/preset/${presetId}`, { method: "POST" }),
  applyCurriculum: (name: string, curriculumId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/${curriculumId}`, { method: "POST" }),
  setCurriculumStage: (name: string, stageIndex: number) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/stage/${stageIndex}`, { method: "POST" }),
  recommend: (name: string) =>
    req<{ hyperparams: PpoHyperparams; parallel: ParallelConfig; notes: string[]; machine: MachineProfile }>(
      `/api/projects/${name}/recommend`,
      { method: "POST" }
    ),
  resetBaseline: (name: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/reset-baseline`, { method: "POST" }),
  validate: (name: string) =>
    req<ValidationResult>(`/api/projects/${name}/validate`, { method: "POST" }),
  exportRl: (name: string) =>
    req<{ task_id: string }>(`/api/projects/${name}/export/rl`, { method: "POST" }),
  trainStatus: () =>
    req<{ running: boolean; project: string | null; task_id: string | null; pid: number | null }>(
      "/api/train/status"
    ),
  startTraining: (name: string, dryRun = false) =>
    req<{ task_id: string; status: string }>(
      `/api/projects/${name}/train/start?dry_run=${dryRun}`,
      { method: "POST" }
    ),
  stopTraining: (name?: string) =>
    req<{ stopped: boolean; project?: string; message?: string }>(
      name ? `/api/projects/${name}/train/stop` : "/api/train/stop",
      { method: "POST" }
    ),
  tensorboardInfo: (name: string) =>
    req<{
      project: string;
      logdir: string;
      latest_run: string | null;
      command: string;
      url: string;
      bind_host: string;
      port: number;
      running: boolean;
    }>(`/api/projects/${name}/train/tensorboard`),
  startTensorboard: (name: string, port = 6006) =>
    req<{
      started: boolean;
      pid?: number;
      port?: number;
      command: string;
      url: string;
      logdir: string;
      message?: string;
      startup_log?: string;
    }>(`/api/projects/${name}/train/tensorboard/start?port=${port}`, { method: "POST" }),
  getTask: (taskId: string) =>
    req<{ task_id: string; status: string; result?: Record<string, string> }>(
      `/api/tasks/${taskId}`
    ),
};
