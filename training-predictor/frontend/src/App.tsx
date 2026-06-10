import { useCallback, useEffect, useRef } from "react";
import { api, streamUrl } from "./api/client";
import type { LogEntry, StudyStatus } from "./api/types";
import { useStudyStore } from "./stores/studyStore";
import { clearActiveRun, loadActiveRun } from "./stores/runPersistence";
import { TopBar } from "./features/topbar/TopBar";
import { StudySetupPanel } from "./features/params/StudySetupPanel";
import { BestPanel } from "./features/prediction/BestPanel";
import { InsightsPanel } from "./features/insights/InsightsPanel";
import { TrialsTable } from "./features/model/TrialsTable";
import { StageProgressPanel } from "./features/stages/StageProgressPanel";
import { ConsolePanel } from "./features/console/ConsolePanel";

export default function App() {
  const store = useStudyStore();
  const esRef = useRef<EventSource | null>(null);
  const trialTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const setError = store.setError;

  // ---- initial load: projects + backend health ----
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [{ projects }, health] = await Promise.all([api.listProjects(), api.health()]);
        if (cancelled) return;
        store.setProjects(projects);
        store.setHealth(health);
        store.setConnected(true);
        if (projects.length && !store.form.project) store.setProject(projects[0]);
      } catch {
        if (cancelled) return;
        store.setConnected(false);
        setError("Backend unreachable — start the Training Predictor API on port 8007 (start_backend.sh).");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshStudies = useCallback(async (proj: string) => {
    try {
      const { studies } = await api.studies(proj);
      useStudyStore.getState().setPastStudies(studies);
    } catch {
      useStudyStore.getState().setPastStudies([]);
    }
    try {
      const { sequences } = await api.sequences(proj);
      useStudyStore.getState().setPastSequences(sequences);
    } catch {
      useStudyStore.getState().setPastSequences([]);
    }
  }, []);

  // ---- load curriculum stages + resumable studies when the project changes ----
  const project = store.form.project;
  useEffect(() => {
    if (!project) {
      useStudyStore.getState().setStages(false, []);
      useStudyStore.getState().setPastStudies([]);
      useStudyStore.getState().setPastSequences([]);
      return;
    }
    let cancelled = false;
    api
      .stages(project)
      .then((r) => {
        if (!cancelled) useStudyStore.getState().setStages(r.enabled, r.stages);
      })
      .catch(() => {
        if (!cancelled) useStudyStore.getState().setStages(false, []);
      });
    void refreshStudies(project);
    return () => {
      cancelled = true;
    };
  }, [project, refreshStudies]);

  const stopStreaming = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    if (trialTimer.current) {
      clearInterval(trialTimer.current);
      trialTimer.current = null;
    }
  }, []);

  const refreshTrials = useCallback(async (taskId: string) => {
    try {
      const { trials } = await api.trials(taskId);
      useStudyStore.getState().setTrials(trials);
    } catch {
      /* transient — keep polling */
    }
  }, []);

  // Open the SSE log/status stream and trial polling for a task. Re-opening the
  // stream replays all logs + status from the start, so this doubles as the
  // reconnect path after a page reload.
  const connectStream = useCallback(
    (taskId: string, project: string) => {
      stopStreaming();
      const es = new EventSource(streamUrl(taskId));
      esRef.current = es;
      es.addEventListener("log", (ev) =>
        useStudyStore.getState().appendLog(JSON.parse((ev as MessageEvent).data) as LogEntry)
      );
      es.addEventListener("status", (ev) =>
        useStudyStore.getState().setStatus(JSON.parse((ev as MessageEvent).data) as StudyStatus)
      );
      es.addEventListener("done", () => {
        void refreshTrials(taskId);
        if (project) void refreshStudies(project);
        stopStreaming();
      });
      es.onerror = () => {
        /* SSE will retry; trial polling + status keep the UI live */
      };
      void refreshTrials(taskId);
      trialTimer.current = setInterval(() => void refreshTrials(taskId), 2500);
    },
    [stopStreaming, refreshTrials, refreshStudies]
  );

  const onStart = useCallback(async () => {
    const { form } = useStudyStore.getState();
    if (!form.project) return;
    setError(null);
    try {
      const { task_id } = await api.start(form);
      useStudyStore.getState().beginRun(task_id);
      connectStream(task_id, form.project);
    } catch (e) {
      setError(`Could not start the study: ${String(e)}`);
    }
  }, [setError, connectStream]);

  // ---- reconnect to an in-flight study after a page reload ----
  useEffect(() => {
    const saved = loadActiveRun();
    if (!saved) return;
    let cancelled = false;
    (async () => {
      try {
        // Confirm the backend still has this task (it 404s if the backend restarted).
        const status = await api.status(saved.taskId);
        if (cancelled) return;
        const s = useStudyStore.getState();
        if (saved.project) s.setProject(saved.project);
        s.beginRun(saved.taskId);
        s.setStatus(status);
        connectStream(saved.taskId, saved.project);
      } catch {
        // Task is gone (e.g. backend restarted) — drop the stale pointer.
        if (!cancelled) clearActiveRun();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [connectStream]);

  const onStop = useCallback(async () => {
    const { taskId } = useStudyStore.getState();
    if (!taskId) return;
    try {
      await api.stop(taskId);
    } catch (e) {
      setError(String(e));
    }
  }, [setError]);

  const onApply = useCallback(async () => {
    const { taskId } = useStudyStore.getState();
    if (!taskId) return;
    if (
      !window.confirm(
        "Save the best trial's parameters into this project's PPO / RL config files?\n\nThe originals are backed up as .bak-<timestamp>."
      )
    )
      return;
    const s = useStudyStore.getState();
    s.setApplying(true);
    s.setApplyResult("Saving…");
    try {
      const d = await api.applyBest(taskId);
      const files = (d.files || []).map((f) => f.split("/").pop()).join(", ");
      let msg: string;
      if (d.mode === "sequential_stage") {
        const stages = d.stages || {};
        const nStages = Object.keys(stages).length;
        const nTerms = Object.values(stages).reduce(
          (n, s) =>
            n +
            Object.keys(s.reward_weights || {}).length +
            Object.values(s.reward_params || {}).reduce((m, p) => m + Object.keys(p).length, 0),
          0
        );
        msg =
          `Saved ${nStages} stage(s), ${nTerms} reward value(s) into per-stage reward terms. ` +
          `Files: ${files || "—"} · ${(d.backups || []).length} backup(s) made.`;
      } else {
        const nHp = Object.keys(d.hyperparameters || {}).length;
        const nW = Object.keys(d.reward_weights || {}).length;
        const nP = Object.keys(d.reward_params || {}).length;
        msg =
          `Saved from trial #${d.applied_from_trial}: ${nHp} hyperparameter(s), ${nW} reward weight(s), ${nP} reward shaping value(s). ` +
          `Files: ${files || "—"} · ${(d.backups || []).length} backup(s) made.`;
      }
      useStudyStore.getState().setApplyResult(msg);
    } catch (e) {
      useStudyStore.getState().setApplyResult(`Save failed: ${String(e)}`);
    } finally {
      useStudyStore.getState().setApplying(false);
    }
  }, []);

  useEffect(() => () => stopStreaming(), [stopStreaming]);

  return (
    <div className="tp-app">
      <TopBar onStart={onStart} onStop={onStop} />

      {store.error ? (
        <div className="tp-errorbar" role="alert">
          <span>{store.error}</span>
          <button type="button" className="tp-error-dismiss" onClick={() => setError(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      ) : null}

      <main className="tp-body">
        <div className="tp-column tp-column-left">
          <StudySetupPanel />
        </div>

        <div className="tp-column tp-column-right">
          <div className="tp-row-2">
            <BestPanel onApply={onApply} />
            <InsightsPanel />
          </div>
          <StageProgressPanel />
          <TrialsTable />
          <ConsolePanel />
        </div>
      </main>
    </div>
  );
}
