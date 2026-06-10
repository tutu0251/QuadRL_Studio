/**
 * Persist a pointer to the in-flight study across page reloads.
 *
 * The study itself keeps running on the backend (a daemon thread registered by
 * task_id), and its trials/decisions are saved to disk. The only thing lost on a
 * reload is the frontend's knowledge of *which* task to reconnect to — so that is
 * all we store here. On mount, App restores this and re-opens the SSE stream,
 * which replays the logs, status and trials.
 */
const KEY = "tp.activeRun";

export interface ActiveRun {
  taskId: string;
  project: string;
}

export function saveActiveRun(taskId: string, project: string): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ taskId, project }));
  } catch {
    /* storage unavailable (private mode / quota) — reconnect just won't survive reload */
  }
}

export function loadActiveRun(): ActiveRun | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ActiveRun>;
    if (!parsed || typeof parsed.taskId !== "string") return null;
    return { taskId: parsed.taskId, project: typeof parsed.project === "string" ? parsed.project : "" };
  } catch {
    return null;
  }
}

export function clearActiveRun(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
