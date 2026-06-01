import type {
  CheckpointInfo,
  ExportBundle,
  ProjectSummary,
  RunInfo,
  ScalarSeries,
  SystemStatsSample,
  TensorBoardStatus,
  TrainStatus,
  WorkspaceOperationBody,
  WorkspaceStatus,
} from "../types";

const DEFAULT_PORT = "8006";

function resolveApiBaseUrl(): string {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:${DEFAULT_PORT}`;
  }
  return `http://127.0.0.1:${DEFAULT_PORT}`;
}

const BASE = resolveApiBaseUrl();

export const getApiBaseUrl = () => BASE;

export const tbOpenUrl = (project: string) =>
  `/api/projects/${encodeURIComponent(project)}/tensorboard/view/`;

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

export const wsTrainLogsUrl = () => {
  const u = new URL(BASE);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  return `${u.origin}/ws/train/logs`;
};

export const api = {
  health: () => req<{ status: string }>("/api/health"),
  listProjects: () =>
    req<{
      projects: string[];
      active: string | null;
      details: ProjectSummary[];
    }>("/api/projects"),
  loadProject: (name: string) =>
    req<{ project: string; summary: ProjectSummary }>(`/api/projects/${name}/load`, {
      method: "POST",
    }),
  getExports: (name: string) => req<ExportBundle>(`/api/projects/${name}/exports`),
  getExportContent: (name: string, path: string) =>
    req<{ path: string; content: string }>(
      `/api/projects/${name}/exports/content?path=${encodeURIComponent(path)}`
    ),
  listCheckpoints: (name: string) =>
    req<{ checkpoints: CheckpointInfo[] }>(`/api/projects/${name}/checkpoints`),
  listRuns: (name: string) => req<{ runs: RunInfo[] }>(`/api/projects/${name}/runs`),
  getScalars: (name: string, runId?: string) =>
    runId
      ? req<{ series: ScalarSeries[] }>(`/api/projects/${name}/runs/${runId}/scalars`)
      : req<{ run_id: string | null; series: ScalarSeries[] }>(`/api/projects/${name}/scalars`),
  trainStatus: (name: string) => req<TrainStatus>(`/api/projects/${name}/train/status`),
  workspaceStatus: (name: string) => req<WorkspaceStatus>(`/api/projects/${name}/workspace/status`),
  workspaceGenerate: (name: string) =>
    req<WorkspaceStatus>(`/api/projects/${name}/workspace/generate`, { method: "POST", body: "{}" }),
  workspaceBuild: (name: string, body: WorkspaceOperationBody = {}) =>
    req<WorkspaceStatus>(`/api/projects/${name}/workspace/build`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  workspaceValidateExports: (name: string) =>
    req<WorkspaceStatus>(`/api/projects/${name}/workspace/validate-exports`, {
      method: "POST",
      body: "{}",
    }),
  workspaceValidate: (name: string, body: WorkspaceOperationBody) =>
    req<WorkspaceStatus>(`/api/projects/${name}/workspace/validate`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  workspaceSetup: (name: string, body: WorkspaceOperationBody) =>
    req<WorkspaceStatus>(`/api/projects/${name}/workspace/setup`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  trainStart: (name: string, body: { dry_run?: boolean; resume_checkpoint?: string } = {}) =>
    req<TrainStatus>(`/api/projects/${name}/train/start`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  trainStop: (name: string) =>
    req<TrainStatus>(`/api/projects/${name}/train/stop`, { method: "POST" }),
  trainResume: (name: string, resume_checkpoint: string, dry_run = false) =>
    req<TrainStatus>(`/api/projects/${name}/train/resume`, {
      method: "POST",
      body: JSON.stringify({ resume_checkpoint, dry_run }),
    }),
  tbStatus: (name: string) => req<TensorBoardStatus>(`/api/projects/${name}/tensorboard/status`),
  tbStart: (name: string, runId?: string) =>
    req<TensorBoardStatus>(
      `/api/projects/${name}/tensorboard/start${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`,
      { method: "POST" }
    ),
  tbStop: (name: string) =>
    req<TensorBoardStatus>(`/api/projects/${name}/tensorboard/stop`, { method: "POST" }),
  systemStats: () => req<SystemStatsSample>("/api/system/stats"),
};
