import type {
  CheckpointInfo,
  CurriculumConfig,
  CurriculumEntry,
  CurriculumInfo,
  GaitType,
  MachineProfile,
  ObservationTerm,
  RamMemorySample,
  RlTrainerModel,
  RewardTerm,
  TerminationConfig,
  TrainingCheckpointConfig,
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

export type ObservationEntry = {
  key: string;
  kind: string;
  topic: string;
  msgType: string;
  rateHz: number;
  parentLink: string;
  fields: string[];
};

export type ObservationsSummary = {
  found: boolean;
  path: string;
  robotName: string | null;
  topicPrefix?: string;
  simUrdf?: string;
  observations: ObservationEntry[];
  kinds: string[];
  jointCount?: number;
  jointNames?: string[];
};

export type ModelPatch = {
  selectedPresetId?: string | null;
  rewardTerms?: RewardTerm[];
  observationTerms?: ObservationTerm[];
  termination?: TerminationConfig;
  curriculum?: CurriculumConfig;
  gaitTypes?: GaitType[];
  curriculumLibrary?: CurriculumEntry[];
  activeCurriculumId?: string | null;
  trainingCheckpoint?: TrainingCheckpointConfig;
  useRecommended?: boolean;
  observationsSetupComplete?: boolean;
  observationWizardDismissed?: boolean;
  customParams?: Record<string, string | number | boolean>;
};

export const api = {
  health: () => req<{ status: string }>("/api/health"),
  machine: () => req<MachineProfile>("/api/machine"),
  machineMemory: () => req<RamMemorySample>("/api/machine/memory"),
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
  getObservations: (name: string) =>
    req<ObservationsSummary>(`/api/projects/${name}/observations`),
  patchModel: (name: string, body: ModelPatch) =>
    req<RlTrainerModel>(`/api/projects/${name}/model`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  applyCurriculum: (name: string, curriculumId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/${curriculumId}`, { method: "POST" }),
  setCurriculumStage: (name: string, stageIndex: number) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/stage/${stageIndex}`, { method: "POST" }),
  listCheckpoints: (name: string) =>
    req<{ checkpoints: CheckpointInfo[] }>(`/api/projects/${name}/checkpoints`),
  addCurriculum: (name: string, body: { name: string; terrainProfile?: string }) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/add`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteCurriculum: (name: string, entryId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/${entryId}`, { method: "DELETE" }),
  duplicateCurriculum: (name: string, entryId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/${entryId}/duplicate`, { method: "POST" }),
  addStage: (name: string, afterOrder?: number) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/stages/add`, {
      method: "POST",
      body: JSON.stringify({ afterOrder }),
    }),
  deleteStage: (name: string, stageId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/stages/${stageId}`, { method: "DELETE" }),
  duplicateStage: (name: string, stageId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/stages/${stageId}/duplicate`, {
      method: "POST",
    }),
  reorderStage: (name: string, stageId: string, direction: "up" | "down") =>
    req<RlTrainerModel>(`/api/projects/${name}/curriculum/stages/${stageId}/reorder`, {
      method: "POST",
      body: JSON.stringify({ direction }),
    }),
  recommendGait: (name: string, gaitId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/recommend/gait/${gaitId}`, { method: "POST" }),
  recommendStage: (name: string, stageId: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/recommend/stage/${stageId}`, { method: "POST" }),
  recommendCurriculum: (name: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/recommend/curriculum`, { method: "POST" }),
  recommendObservations: (name: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/recommend/observations`, { method: "POST" }),
  syncObservations: (name: string) =>
    req<RlTrainerModel>(`/api/projects/${name}/observations/sync`, { method: "POST" }),
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
  servicesStatus: () =>
    req<{
      checkedAt: string;
      hostname: string;
      overall: "running" | "partial" | "stopped";
      runningCount: number;
      totalServices: number;
      uptimeSeconds?: number | null;
      systemdActive?: boolean | null;
      services: {
        id: string;
        label: string;
        backendPort: number;
        frontendPort: number;
        backendUp: boolean;
        frontendUp: boolean;
        state: "running" | "partial" | "stopped";
      }[];
    }>("/api/services/status"),
  restartServices: (scope = "all", delaySeconds = 2) =>
    req<{ message: string }>(
      `/api/services/restart?scope=${encodeURIComponent(scope)}&delay_seconds=${delaySeconds}`,
      { method: "POST" }
    ),
  rebootMachine: (delaySeconds = 5) =>
    req<{ message: string }>(
      `/api/system/reboot?confirm=true&delay_seconds=${delaySeconds}`,
      { method: "POST" }
    ),
};
