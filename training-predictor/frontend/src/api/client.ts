import type {
  ApplyResult,
  BestTrial,
  Decision,
  Health,
  LogEntry,
  StageResult,
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

  // ---- persisted results (read from disk; survive reload + backend restart) ----
  studyBest: (project: string, name: string) =>
    req<{ best: BestTrial | null; decisions: Decision[]; study_name: string }>(
      `/api/projects/${project}/studies/${encodeURIComponent(name)}/best`
    ),
  sequenceBest: (project: string, name: string) =>
    req<{ stages: StageResult[]; seq_name: string }>(
      `/api/projects/${project}/sequences/${encodeURIComponent(name)}/best`
    ),
  applyStudyPersisted: (project: string, name: string) =>
    req<ApplyResult>(`/api/projects/${project}/studies/${encodeURIComponent(name)}/apply`, {
      method: "POST",
    }),
  applySequencePersisted: (project: string, name: string) =>
    req<ApplyResult>(`/api/projects/${project}/sequences/${encodeURIComponent(name)}/apply`, {
      method: "POST",
    }),
};
