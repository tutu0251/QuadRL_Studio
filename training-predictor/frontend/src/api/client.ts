import type {
  ApplyResult,
  Health,
  LogEntry,
  StagesResponse,
  StartRequest,
  SequenceSummary,
  StartResponse,
  StudySummary,
  StudyStatus,
  TrialRow,
} from "./types";

/** Backend base — the Training Predictor API (start_backend.sh defaults to port 8007). */
export const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8007";

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

/** Server-Sent-Events URL for a running study's log + status stream. */
export const streamUrl = (taskId: string) => `${BASE}/api/tuning/${taskId}/stream`;

export const api = {
  health: () => req<Health>("/api/health"),
  listProjects: () => req<{ projects: string[] }>("/api/projects"),
  stages: (project: string) => req<StagesResponse>(`/api/projects/${project}/stages`),
  studies: (project: string) => req<{ studies: StudySummary[] }>(`/api/projects/${project}/studies`),
  sequences: (project: string) =>
    req<{ sequences: SequenceSummary[] }>(`/api/projects/${project}/sequences`),
  start: (body: StartRequest) =>
    req<StartResponse>("/api/tuning/start", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  status: (taskId: string) => req<StudyStatus>(`/api/tuning/${taskId}/status`),
  trials: (taskId: string) => req<{ trials: TrialRow[] }>(`/api/tuning/${taskId}/trials`),
  logsSince: (taskId: string, since: number) =>
    req<{ entries: LogEntry[]; next: number }>(`/api/tuning/${taskId}/logs?since=${since}`),
  stop: (taskId: string) =>
    req<{ ok: boolean; status: string }>(`/api/tuning/${taskId}/stop`, { method: "POST" }),
  applyBest: (taskId: string) =>
    req<ApplyResult>(`/api/tuning/${taskId}/apply`, { method: "POST" }),
};
