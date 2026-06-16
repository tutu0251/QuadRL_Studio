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

/**
 * Persist which past study/sequence is being *previewed* (so its best params can be
 * applied), separately from any in-flight run. Restored on reload so the page comes
 * back showing the same results, ready to "Save to project".
 */
const PREVIEW_KEY = "tp.preview";

export interface PreviewSelection {
  project: string;
  mode: "global" | "sequential_stage";
  name: string;
}

export function savePreview(sel: PreviewSelection): void {
  try {
    localStorage.setItem(PREVIEW_KEY, JSON.stringify(sel));
  } catch {
    /* storage unavailable — preview just won't survive reload */
  }
}

export function loadPreview(): PreviewSelection | null {
  try {
    const raw = localStorage.getItem(PREVIEW_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Partial<PreviewSelection>;
    if (!p || typeof p.name !== "string" || typeof p.project !== "string") return null;
    if (p.mode !== "global" && p.mode !== "sequential_stage") return null;
    return { project: p.project, mode: p.mode, name: p.name };
  } catch {
    return null;
  }
}

export function clearPreview(): void {
  try {
    localStorage.removeItem(PREVIEW_KEY);
  } catch {
    /* ignore */
  }
}
