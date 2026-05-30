import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client";
import { useTrainerStore } from "../../stores/trainerStore";
import { resolveTensorboardUrl } from "../../utils/tensorboardUrl";

async function pollTask(taskId: string, max = 7200) {
  for (let i = 0; i < max; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const t = await api.getTask(taskId);
    if (t.status === "completed" || t.status === "failed" || t.status === "cancelled") {
      return t;
    }
  }
  return null;
}

export function Toolbar() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const setValidation = useTrainerStore((s) => s.setValidation);
  const validation = useTrainerStore((s) => s.validation);
  const training = useTrainerStore((s) => s.training);
  const setTraining = useTrainerStore((s) => s.setTraining);
  const log = useTrainerStore((s) => s.log);
  const [busy, setBusy] = useState(false);

  const refreshTrainStatus = useCallback(async () => {
    try {
      const st = await api.trainStatus();
      setTraining({
        running: st.running,
        project: st.project,
        taskId: st.task_id,
        pid: st.pid,
      });
    } catch {
      /* ignore */
    }
  }, [setTraining]);

  useEffect(() => {
    void refreshTrainStatus();
    const id = setInterval(() => void refreshTrainStatus(), 2000);
    return () => clearInterval(id);
  }, [refreshTrainStatus]);

  const recommend = async () => {
    if (!project || busy || training.running) return;
    setBusy(true);
    try {
      const r = await api.recommend(project);
      const m = await api.getModel(project);
      setModel(m);
      r.notes.forEach((n) => log(n));
      log("Machine recommendations applied");
      setValidation(await api.validate(project));
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    if (!project || busy || training.running) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      setValidation(v);
      if (v.valid) log(`Validation OK (${v.warnings.length} warnings)`);
      else log(`Validation failed: ${v.errors.length} errors`);
      v.errors.slice(0, 5).forEach((e) => log(`  · ${e.message}`));
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const exportRl = async () => {
    if (!project || busy || training.running) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      setValidation(v);
      if (!v.valid) {
        log(`Validation failed (${v.errors.length} errors)`);
        return;
      }
      const { task_id } = await api.exportRl(project);
      log("Exporting rl_<project>_config.yaml…");
      const t = await pollTask(task_id, 120);
      if (t?.status === "completed") log(`Export complete: ${t.result?.rl_config ?? ""}`);
      else log("Export failed");
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const watchTrainingTask = useCallback(
    (taskId: string) => {
      void (async () => {
        const t = await pollTask(taskId);
        await refreshTrainStatus();
        if (t?.status === "completed") {
          log(`Training complete — checkpoints: ${t.result?.checkpoints ?? "see project/checkpoints"}`);
          if (t.result?.tensorboard_logdir) {
            log(`TensorBoard: tensorboard --logdir ${t.result.tensorboard_logdir}`);
          }
        } else if (t?.status === "cancelled") {
          log("Training stopped");
        } else if (t?.status === "failed") {
          log("Training failed — see console");
        }
      })();
    },
    [log, refreshTrainStatus]
  );

  const startTraining = async () => {
    if (!project || busy || training.running) return;
    setBusy(true);
    try {
      const v = await api.validate(project);
      setValidation(v);
      if (!v.valid) {
        log(`Cannot start: ${v.errors.length} validation errors`);
        return;
      }
      log("Starting training…");
      const { task_id } = await api.startTraining(project);
      setTraining({ running: true, project, taskId: task_id, pid: null });
      log(`Training started (task ${task_id.slice(0, 8)}…)`);
      watchTrainingTask(task_id);
    } catch (e) {
      log(String(e));
      await refreshTrainStatus();
    } finally {
      setBusy(false);
    }
  };

  const stopTrainingRun = async () => {
    if (!training.running) return;
    try {
      await api.stopTraining(training.project ?? project ?? undefined);
      log("Stop signal sent");
      await refreshTrainStatus();
    } catch (e) {
      log(String(e));
    }
  };

  const openTensorboard = async () => {
    if (!project || busy) return;
    setBusy(true);
    try {
      const info = await api.tensorboardInfo(project);
      log(`TensorBoard logdir: ${info.logdir}`);
      if (info.latest_run) log(`Latest run: ${info.latest_run}`);
      try {
        const started = await api.startTensorboard(project);
        const url = resolveTensorboardUrl(started.url, started.port ?? 6006);
        if (started.started) {
          log(`TensorBoard started — open ${url} (PID ${started.pid})`);
        } else {
          log(started.message ?? `TensorBoard already running — open ${url}`);
        }
        if (started.startup_log) {
          started.startup_log.split("\n").slice(-3).forEach((line) => log(line));
        }
        window.open(url, "_blank", "noopener,noreferrer");
      } catch (startErr) {
        const msg = startErr instanceof Error ? startErr.message : String(startErr);
        log(`TensorBoard start failed: ${msg}`);
        const fallbackUrl = resolveTensorboardUrl(info.url, info.port ?? 6006);
        log(`CLI: ${info.command}`);
        log(`Then open ${fallbackUrl}`);
      }
    } catch (e) {
      log(String(e));
    } finally {
      setBusy(false);
    }
  };

  const trainingThisProject = training.running && training.project === project;

  return (
    <div className="toolbar">
      <div className="toolbar-group toolbar-group-train">
        <span className="toolbar-label">Train</span>
        <button
          type="button"
          className="toolbar-btn train-start"
          disabled={!project || busy || training.running}
          onClick={() => void startTraining()}
          title="Validate, export config, and run PPO training"
        >
          Start training
        </button>
        {trainingThisProject && (
          <button
            type="button"
            className="toolbar-btn train-stop"
            onClick={() => void stopTrainingRun()}
          >
            Stop training
          </button>
        )}
        {training.running && (
          <span className="toolbar-chip train-running">
            {trainingThisProject ? "Running" : `Busy: ${training.project}`}
          </span>
        )}
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy}
          onClick={() => void openTensorboard()}
          title="Start TensorBoard for project runs/ (falls back to CLI hint)"
        >
          TensorBoard
        </button>
      </div>

      <span className="toolbar-divider" />

      <div className="toolbar-group">
        <span className="toolbar-label">Tune</span>
        <button
          type="button"
          className="toolbar-btn primary"
          disabled={!project || busy || training.running}
          onClick={() => void recommend()}
        >
          Recommend
        </button>
      </div>

      <span className="toolbar-divider" />

      <div className="toolbar-group">
        <span className="toolbar-label">Check</span>
        <button
          type="button"
          className="toolbar-btn"
          disabled={!project || busy || training.running}
          onClick={() => void validate()}
        >
          Validate
        </button>
        {validation && (
          <span className={`toolbar-chip ${validation.valid ? "ok" : "err"}`}>
            {validation.valid ? "OK" : `${validation.errors.length} err`}
          </span>
        )}
      </div>

      <span className="toolbar-divider" />

      <div className="toolbar-group">
        <button
          type="button"
          className="toolbar-btn accent"
          disabled={!project || busy || training.running}
          onClick={() => void exportRl()}
        >
          Export YAML
        </button>
      </div>

      <span className="toolbar-spacer" />
      {busy && <span className="toolbar-busy">Working…</span>}
      {model && project && (
        <span className="toolbar-context mono">
          {model.parallel.numEnvs} env · {enabledTerms(model)} rewards
          {model.curriculum.enabled ? " · curriculum" : ""}
        </span>
      )}
    </div>
  );
}

function enabledTerms(model: { rewardTerms: { enabled: boolean }[] }): number {
  return model.rewardTerms.filter((t) => t.enabled).length;
}
