import type {
  CurriculumConfig,
  CurriculumInfo,
  MachineProfile,
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

export type ModelPatch = {
  selectedPresetId?: string | null;
  rewardTerms?: RewardTerm[];
  termination?: TerminationConfig;
  curriculum?: CurriculumConfig;
  customParams?: Record<string, string | number | boolean>;
};

export const api = {
  health: () => req<{ status: string }>("/api/health"),
  machine: () => req<MachineProfile>("/api/machine"),
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
  applyCurriculum: (name: string, curriculumId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/${curriculumId}`, { method: "POST" }),
  setCurriculumStage: (name: string, stageIndex: number) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/stage/${stageIndex}`, { method: "POST" }),
  refreshMachineProfile: (name: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/machine-profile`, { method: "POST" }),
  validate: (name: string) =>
    req<ValidationResult>(`/api/projects/${name}/validate`, { method: "POST" }),
  exportRl: (name: string) =>
    req<{ task_id: string }>(`/api/projects/${name}/export/rl`, { method: "POST" }),
  getTask: (taskId: string) =>
    req<{ task_id: string; status: string; result?: Record<string, string> }>(
      `/api/tasks/${taskId}`
    ),
};
