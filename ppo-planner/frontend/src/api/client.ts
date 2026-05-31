import type {
  MachineProfile,
  OutputPatch,
  ParallelConfig,
  PpoHyperparams,
  PpoPlannerModel,
  ValidationResult,
} from "@ppo-model";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8004";

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

export type PpoParamsPatch = Partial<PpoHyperparams> & { useRecommended?: boolean };
export type ParallelPatch = Partial<ParallelConfig> & { useRecommended?: boolean };

export const api = {
  health: () => req<{ status: string }>("/api/health"),
  machine: () => req<MachineProfile>("/api/machine"),
  listProjects: () =>
    req<{
      projects: string[];
      active: string | null;
      details: { name: string; hasSensor: boolean; hasPpo: boolean }[];
    }>("/api/projects"),
  loadProject: (name: string) =>
    req<{ project: string; model: PpoPlannerModel; hasPpo: boolean }>(
      `/api/projects/${name}/load`,
      { method: "POST" }
    ),
  bootstrap: (name: string) =>
    req<{ project: string; model: PpoPlannerModel }>(`/api/projects/${name}/bootstrap`, {
      method: "POST",
    }),
  getModel: (name: string) => req<PpoPlannerModel>(`/api/projects/${name}/model`),
  patchParams: (name: string, body: PpoParamsPatch) =>
    req<PpoPlannerModel>(`/api/projects/${name}/params`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  patchParallel: (name: string, body: ParallelPatch) =>
    req<PpoPlannerModel>(`/api/projects/${name}/parallel`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  patchOutput: (name: string, body: OutputPatch) =>
    req<PpoPlannerModel>(`/api/projects/${name}/output`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  recommend: (name: string) =>
    req<{ params: PpoHyperparams; parallel: ParallelConfig; notes: string[]; machine: MachineProfile }>(
      `/api/projects/${name}/recommend`,
      { method: "POST" }
    ),
  resetBaseline: (name: string) =>
    req<PpoPlannerModel>(`/api/projects/${name}/reset-baseline`, { method: "POST" }),
  validate: (name: string) =>
    req<ValidationResult>(`/api/projects/${name}/validate`, { method: "POST" }),
  exportPpo: (name: string) =>
    req<{ task_id: string }>(`/api/projects/${name}/export/ppo`, { method: "POST" }),
  getTask: (taskId: string) =>
    req<{ task_id: string; status: string; result?: Record<string, string | string[]> }>(
      `/api/tasks/${taskId}`
    ),
};
