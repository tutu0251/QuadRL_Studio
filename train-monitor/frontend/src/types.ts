export type LogLevel = "debug" | "info" | "warn" | "error";

export type LogEntry = {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  component?: string;
};

export type WsLogPayload = {
  timestamp: string;
  level: string;
  message: string;
  component?: string;
};

export type ExportFileInfo = {
  category: string;
  filename: string;
  path: string;
  size_bytes: number;
  modified_at: string;
  format: string;
};

export type ExportBundle = {
  project: string;
  exports_dir: string;
  files: ExportFileInfo[];
  missing_required: string[];
  ready_for_training: boolean;
  workspace_ready?: boolean;
  sensor_exports_ready?: boolean;
  recommended_sim_backend?: string;
};

export type CheckpointInfo = {
  path: string;
  filename: string;
  size_bytes: number;
  modified_at: string;
};

export type RunStageInfo = {
  name: string;
  logdir: string;
  has_events: boolean;
};

export type RunInfo = {
  run_id: string;
  path: string;
  started_at?: string | null;
  ended_at?: string | null;
  status: "running" | "completed" | "failed" | "stopped" | "unknown";
  config?: string | null;
  tensorboard_logdir?: string | null;
  curriculum_enabled: boolean;
  stages: RunStageInfo[];
  pid?: number | null;
};

export type ScalarSeries = {
  tag: string;
  steps: number[];
  values: number[];
};

export type TrainStatus = {
  project: string;
  state: "idle" | "starting" | "running" | "stopping" | "failed";
  pid?: number | null;
  run_id?: string | null;
  started_at?: string | null;
  current_stage?: string | null;
  progress_message?: string | null;
  resume_checkpoint?: string | null;
  dry_run: boolean;
  exit_code?: number | null;
};

export type TensorBoardStatus = {
  running: boolean;
  url?: string | null;
  embed_url?: string | null;
  open_url?: string | null;
  port?: number | null;
  logdir?: string | null;
  run_id?: string | null;
  error?: string | null;
};

export type SystemStatsSample = {
  sampledAt: string;
  hostname: string;
  cpuPercent: number;
  cpuCountLogical: number;
  ramTotalMb: number;
  ramUsedMb: number;
  ramAvailableMb: number;
  ramUsedPercent: number;
  ramTotalGb: number;
  ramUsedGb: number;
  gpuAvailable: boolean;
  gpuName: string;
  gpuUtilPercent?: number | null;
  gpuMemoryUsedMb?: number | null;
  gpuMemoryTotalMb?: number | null;
  gpuMemoryPercent?: number | null;
};

export type ProjectSummary = {
  name: string;
  has_rl_export: boolean;
  has_ppo_export: boolean;
  export_count: number;
  checkpoint_count: number;
  run_count: number;
  training_state: string;
};

export type WorkspaceStatus = {
  project: string;
  state: "idle" | "starting" | "running" | "failed";
  operation?: string | null;
  workspace_path?: string | null;
  manifest_present: boolean;
  build_ready: boolean;
  exports_stale: boolean;
  stale_reasons: string[];
  readiness_status?: string | null;
  training_ready: boolean;
  sensor_exports_ready: boolean;
  recommended_sim_backend: string;
  last_result?: Record<string, unknown> | null;
  error?: string | null;
  finished_at?: string | null;
};

export type WorkspaceOperationBody = {
  clean?: boolean;
  static_only?: boolean;
  skip_runtime?: boolean;
  skip_build?: boolean;
};
