import { useEffect } from "react";
import { useCommandPreview } from "../../hooks/useCommandPreview";
import { CheckpointsPanel } from "../checkpoints/CheckpointsPanel";
import { RunsPanel } from "../runs/RunsPanel";
import { SystemResourcesPanel } from "../system/SystemResourcesPanel";
import { MetricsPanel } from "../tensorboard/MetricsPanel";
import { TrainingPanel } from "../training/TrainingPanel";
import { useMonitorStore } from "../../stores/monitorStore";
import type { ExportBundle, TensorBoardStatus, TrainStatus, WorkspaceStatus } from "../../types";

type Props = {
  project: string | null;
  exports: ExportBundle | null;
  trainStatus: TrainStatus | null;
  workspaceStatus: WorkspaceStatus | null;
  checkpoints: ReturnType<typeof useMonitorStore.getState>["checkpoints"];
  runs: ReturnType<typeof useMonitorStore.getState>["runs"];
  scalars: ReturnType<typeof useMonitorStore.getState>["scalars"];
  selectedRunId: string | null;
  selectedCheckpoint: string | null;
  selectedStageLogdir: string | null;
  tbStatus: TensorBoardStatus | null;
  dryRun: boolean;
  gazeboHeadless: boolean;
  guiAvailable: boolean;
  resolvedDisplay: string | null;
  busy: boolean;
  trainingActive: boolean;
  onDryRunChange: (v: boolean) => void;
  onGazeboHeadlessChange: (v: boolean) => void;
  onStart: () => void;
  onStop: () => void;
  onResume: () => void;
  onSelectCheckpoint: (path: string | null) => void;
  onSelectRun: (runId: string) => void;
  onSelectStage: (logdir: string | null) => void;
  onOpenTb: () => void;
  onStopTb: () => void;
};

export function MetricMonitorPage({
  project,
  exports,
  trainStatus,
  workspaceStatus,
  checkpoints,
  runs,
  scalars,
  selectedRunId,
  selectedCheckpoint,
  selectedStageLogdir,
  tbStatus,
  dryRun,
  gazeboHeadless,
  guiAvailable,
  resolvedDisplay,
  busy,
  trainingActive,
  onDryRunChange,
  onGazeboHeadlessChange,
  onStart,
  onStop,
  onResume,
  onSelectCheckpoint,
  onSelectRun,
  onSelectStage,
  onOpenTb,
  onStopTb,
}: Props) {
  const setConsoleFilter = useMonitorStore((s) => s.setConsoleFilter);

  useEffect(() => {
    setConsoleFilter(null);
  }, [setConsoleFilter]);

  const startPreview = useCommandPreview(project, "train_start", {
    dry_run: dryRun,
    gazebo_headless: gazeboHeadless,
  });
  const stopPreview = useCommandPreview(project, "train_stop");
  const resumePreview = useCommandPreview(project, "train_resume", {
    dry_run: dryRun,
    gazebo_headless: gazeboHeadless,
    resume_checkpoint: selectedCheckpoint ?? "",
  });
  const tbStartPreview = useCommandPreview(project, "tensorboard_start", { run_id: selectedRunId });
  const tbStopPreview = useCommandPreview(project, "tensorboard_stop");

  const selectedRun = runs.find((r) => r.run_id === selectedRunId) ?? null;
  const filteredScalars =
    selectedStageLogdir && selectedRun?.curriculum_enabled
      ? scalars.filter((s) => {
          const stage = selectedRun.stages.find((st) => st.logdir === selectedStageLogdir);
          if (!stage) return true;
          const slug = stage.logdir.split("/").pop() ?? "";
          return s.tag.includes(slug) || true;
        })
      : scalars;

  return (
    <div className="page-grid metric-page">
      <aside className="metric-side">
        <TrainingPanel
          project={project}
          status={trainStatus}
          ready={exports?.ready_for_training ?? false}
          selectedCheckpoint={selectedCheckpoint}
          dryRun={dryRun}
          gazeboHeadless={gazeboHeadless}
          recommendedSim={
            workspaceStatus?.recommended_sim_backend ?? exports?.recommended_sim_backend ?? "unavailable"
          }
          guiAvailable={guiAvailable}
          resolvedDisplay={resolvedDisplay}
          onDryRunChange={onDryRunChange}
          onGazeboHeadlessChange={onGazeboHeadlessChange}
          onStart={onStart}
          onStop={onStop}
          onResume={onResume}
          busy={busy}
          startCommand={startPreview.preview?.command ?? trainStatus?.command}
          stopCommand={stopPreview.preview?.command}
          resumeCommand={resumePreview.preview?.command}
          startCommandLoading={startPreview.loading}
          stopCommandLoading={stopPreview.loading}
          resumeCommandLoading={resumePreview.loading}
        />
        <CheckpointsPanel checkpoints={checkpoints} selected={selectedCheckpoint} onSelect={onSelectCheckpoint} />
        <RunsPanel
          runs={runs}
          selectedRunId={selectedRunId}
          selectedStageLogdir={selectedStageLogdir}
          onSelect={onSelectRun}
          onSelectStage={onSelectStage}
        />
        <SystemResourcesPanel />
      </aside>
      <main className="metric-main">
        <MetricsPanel
          project={project}
          scalars={filteredScalars}
          tbStatus={tbStatus}
          trainingActive={trainingActive}
          onOpenTb={onOpenTb}
          onStopTb={onStopTb}
          busy={busy}
          tbStartCommand={tbStartPreview.preview?.command}
          tbStopCommand={tbStopPreview.preview?.command}
          tbStartLoading={tbStartPreview.loading}
          tbStopLoading={tbStopPreview.loading}
        />
      </main>
    </div>
  );
}
