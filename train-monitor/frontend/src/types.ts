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
  port?: number | null;
  logdir?: string | null;
  run_id?: string | null;
  error?: string | null;
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
