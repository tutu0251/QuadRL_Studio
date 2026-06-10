import type {
  CheckpointInfo,
  CommandPreview,
  ExportBundle,
  ProjectSummary,
  RunInfo,
  ScalarSeries,
  SpawnConfig,
  SpawnOffset,
  SpawnTestResult,
  SpawnTestStatus,
  SystemStatsSample,
  TensorBoardStatus,
  TopicWatchStatus,
  TopicsBundle,
  TrainStatus,
  TrainingConfig,
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
    try {
      const j = JSON.parse(text) as { detail?: string | { msg?: string } };
      const d = j.detail;
      if (typeof d === "string") throw new Error(d);
      if (d && typeof d === "object" && "msg" in d) throw new Error(String(d.msg));
    } catch (e) {
      if (e instanceof Error && e.message !== text) throw e;
    }
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
  getScalars: (name: string, runId?: string, stage?: string) =>
    runId
      ? req<{ series: ScalarSeries[] }>(
          `/api/projects/${name}/runs/${runId}/scalars${stage ? `?stage=${encodeURIComponent(stage)}` : ""}`
        )
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
  trainStart: (
    name: string,
    body: { dry_run?: boolean; gazebo_headless?: boolean; resume_checkpoint?: string } = {}
  ) =>
    req<TrainStatus>(`/api/projects/${name}/train/start`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  trainStop: (name: string) =>
    req<TrainStatus>(`/api/projects/${name}/train/stop`, { method: "POST" }),
  trainResume: (
    name: string,
    resume_checkpoint: string,
    options: {
      dry_run?: boolean;
      gazebo_headless?: boolean;
      resume_start_stage?: number;
      reset_log_std?: boolean;
      vf_coef?: number;
    } = {}
  ) =>
    req<TrainStatus>(`/api/projects/${name}/train/resume`, {
      method: "POST",
      body: JSON.stringify({ resume_checkpoint, ...options }),
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
  displayStatus: () =>
    req<{ gui_available: boolean; resolved_display?: string | null; env_display?: string | null }>(
      "/api/system/display"
    ),
  getCommandPreview: (name: string, action: string, params?: Record<string, unknown>) =>
    req<CommandPreview>(
      `/api/projects/${name}/commands/preview?action=${encodeURIComponent(action)}${
        params ? `&params=${encodeURIComponent(JSON.stringify(params))}` : ""
      }`
    ),
  getSpawnConfig: (name: string) => req<SpawnConfig>(`/api/projects/${name}/spawn-config`),
  patchSpawnConfig: (
    name: string,
    body: Partial<{
      spawn_offset: SpawnOffset;
      controller_apply_delay_s: number;
      pose_confirmed: boolean;
    }>
  ) =>
    req<SpawnConfig & { command: string }>(`/api/projects/${name}/spawn-config`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  testSpawn: (name: string, body: { headless?: boolean } = {}) =>
    req<SpawnTestResult>(`/api/projects/${name}/spawn/test`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getSpawnTestStatus: (name: string) =>
    req<SpawnTestStatus>(`/api/projects/${name}/spawn/test/status`),
  stopSpawnTest: (name: string) =>
    req<SpawnTestStatus & { command: string }>(`/api/projects/${name}/spawn/test/stop`, {
      method: "POST",
    }),
  getTopics: (name: string) => req<TopicsBundle>(`/api/projects/${name}/topics`),
  patchTopicConfirmations: (name: string, confirmed_topics: string[]) =>
    req<TopicsBundle & { command: string }>(`/api/projects/${name}/topics/confirmations`, {
      method: "PATCH",
      body: JSON.stringify({ confirmed_topics }),
    }),
  getTopicWatchStatus: (name: string) =>
    req<TopicWatchStatus>(`/api/projects/${name}/topics/watch/status`),
  startTopicWatch: (name: string, topics: string[] = []) =>
    req<TopicWatchStatus>(`/api/projects/${name}/topics/watch/start`, {
      method: "POST",
      body: JSON.stringify({ topics }),
    }),
  stopTopicWatch: (name: string) =>
    req<TopicWatchStatus>(`/api/projects/${name}/topics/watch/stop`, { method: "POST" }),
  getTrainingConfig: (name: string) => req<TrainingConfig>(`/api/projects/${name}/training-config`),
  patchTrainingConfig: (
    name: string,
    body: Partial<{
      action_scales: { joint: string; action_scale: number; default_position?: number }[];
      observation_scales: {
        id: string;
        key: string;
        topic?: string;
        scale: number;
        offset: number;
        clip_min?: number | null;
        clip_max?: number | null;
        enabled?: boolean;
      }[];
    }>
  ) =>
    req<TrainingConfig & { command: string }>(`/api/projects/${name}/training-config`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};
