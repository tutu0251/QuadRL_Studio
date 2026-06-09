import { useCommandPreview } from "../../hooks/useCommandPreview";
import { CheckpointsPanel } from "../checkpoints/CheckpointsPanel";
import { RunsPanel } from "../runs/RunsPanel";
import { SystemResourcesPanel } from "../system/SystemResourcesPanel";
import { MetricsPanel } from "../tensorboard/MetricsPanel";
import { TensorBoardPanel } from "../tensorboard/TensorBoardPanel";
import { TrainingPanel } from "../training/TrainingPanel";
import { useMonitorStore } from "../../stores/monitorStore";
import type { ExportBundle, StageInfo, TensorBoardStatus, TrainStatus } from "../../types";

type Props = {
  project: string | null;
  exports: ExportBundle | null;
  trainStatus: TrainStatus | null;
  checkpoints: ReturnType<typeof useMonitorStore.getState>["checkpoints"];
  runs: ReturnType<typeof useMonitorStore.getState>["runs"];
  scalars: ReturnType<typeof useMonitorStore.getState>["scalars"];
  selectedRunId: string | null;
  selectedCheckpoint: string | null;
  stages: StageInfo[];
  tbStatus: TensorBoardStatus | null;
  gazeboHeadless: boolean;
  guiAvailable: boolean;
  resolvedDisplay: string | null;
  resetLogStd: boolean;
  busy: boolean;
  trainingActive: boolean;
  onGazeboHeadlessChange: (v: boolean) => void;
  onResetLogStdChange: (v: boolean) => void;
  onStart: () => void;
  onStop: () => void;
  onResume: () => void;
  onStartFromStage: (stageIndex: number) => void;
  onSelectCheckpoint: (path: string | null) => void;
  onSelectRun: (runId: string) => void;
  onOpenTb: () => void;
  onStopTb: () => void;
};

export function MetricMonitorPage({
  project,
  exports,
  trainStatus,
  checkpoints,
  runs,
  scalars,
  selectedRunId,
  selectedCheckpoint,
  stages,
  tbStatus,
  gazeboHeadless,
  guiAvailable,
  resolvedDisplay,
  resetLogStd,
  busy,
  trainingActive,
  onGazeboHeadlessChange,
  onResetLogStdChange,
  onStart,
  onStop,
  onResume,
  onStartFromStage,
  onSelectCheckpoint,
  onSelectRun,
  onOpenTb,
  onStopTb,
}: Props) {
  const startPreview = useCommandPreview(project, "train_start", {
    gazebo_headless: gazeboHeadless,
  });
  const stopPreview = useCommandPreview(project, "train_stop");
  const resumePreview = useCommandPreview(project, "train_resume", {
    gazebo_headless: gazeboHeadless,
    resume_checkpoint: selectedCheckpoint ?? "",
    reset_log_std: resetLogStd,
  });
  const tbStartPreview = useCommandPreview(project, "tensorboard_start", { run_id: selectedRunId });
  const tbStopPreview = useCommandPreview(project, "tensorboard_stop");

  const selectedRun = runs.find((r) => r.run_id === selectedRunId) ?? null;

  return (
    <div className="page-grid metric-page">
      <aside className="metric-side">
        <TrainingPanel
          project={project}
          status={trainStatus}
          ready={exports?.ready_for_training ?? false}
          selectedCheckpoint={selectedCheckpoint}
          stages={stages}
          gazeboHeadless={gazeboHeadless}
          guiAvailable={guiAvailable}
          resolvedDisplay={resolvedDisplay}
          resetLogStd={resetLogStd}
          onGazeboHeadlessChange={onGazeboHeadlessChange}
          onResetLogStdChange={onResetLogStdChange}
          onStart={onStart}
          onStop={onStop}
          onResume={onResume}
          onStartFromStage={onStartFromStage}
          busy={busy}
          startCommand={startPreview.preview?.command ?? trainStatus?.command}
          stopCommand={stopPreview.preview?.command}
          resumeCommand={resumePreview.preview?.command}
          startCommandLoading={startPreview.loading}
          stopCommandLoading={stopPreview.loading}
          resumeCommandLoading={resumePreview.loading}
        />
        <CheckpointsPanel checkpoints={checkpoints} selected={selectedCheckpoint} onSelect={onSelectCheckpoint} />
        <RunsPanel runs={runs} selectedRunId={selectedRunId} onSelect={onSelectRun} />
        <TensorBoardPanel
          project={project}
          tbStatus={tbStatus}
          busy={busy}
          onOpenTb={onOpenTb}
          onStopTb={onStopTb}
          tbStartCommand={tbStartPreview.preview?.command}
          tbStopCommand={tbStopPreview.preview?.command}
          tbStartLoading={tbStartPreview.loading}
          tbStopLoading={tbStopPreview.loading}
        />
      </aside>
      <main className="metric-main">
        <MetricsPanel
          project={project}
          runId={selectedRunId}
          scalars={scalars}
          stages={selectedRun?.stages ?? []}
          curriculumEnabled={selectedRun?.curriculum_enabled ?? false}
          trainingActive={trainingActive}
          headerExtra={<SystemResourcesPanel compact />}
        />
      </main>
    </div>
  );
}
