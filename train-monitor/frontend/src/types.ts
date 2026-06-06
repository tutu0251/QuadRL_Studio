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

export type DisplayStatus = {
  gui_available: boolean;
  resolved_display?: string | null;
  env_display?: string | null;
};

export type TrainStatus = {
  project: string;
  state: "idle" | "starting" | "running" | "stopping" | "failed";
  pid?: number | null;
  run_id?: string | null;
  started_at?: string | null;
  current_stage?: string | null;
  progress_message?: string | null;
  rollout_count?: number | null;
  episode_count?: number | null;
  last_termination_reason?: string | null;
  termination_counts?: Record<string, number> | null;
  resume_checkpoint?: string | null;
  dry_run: boolean;
  gazebo_headless?: boolean;
  exit_code?: number | null;
  command?: string | null;
};

export type SpawnTestState = "idle" | "starting" | "running" | "stopping";

export type SpawnTestStatus = {
  project: string;
  state: SpawnTestState;
  headless: boolean;
  spawn_valid: boolean;
  pid?: number | null;
  errors: string[];
  command?: string;
};

export type SpawnTestResult = {
  project: string;
  valid: boolean;
  status: string;
  state?: SpawnTestState;
  headless?: boolean;
  pid?: number | null;
  details?: Record<string, unknown> | null;
  errors: string[];
  warnings: string[];
  command?: string;
  stop_command?: string;
};

export type MonitorPageId = "spawn" | "topic" | "training" | "metric";

export type CommandPreview = {
  action: string;
  command: string;
  description?: string;
};

export type SpawnOffset = {
  dx: number;
  dy: number;
  dz: number;
  droll: number;
  dpitch: number;
  dyaw: number;
};

export type SpawnConfig = {
  project: string;
  export_path: string;
  pose_name: string;
  base_spawn: Record<string, number>;
  spawn_offset: SpawnOffset;
  effective_spawn: Record<string, number>;
  joints: Record<string, number>;
  controller_apply_delay_s: number;
  pose_confirmed: boolean;
  missing_export: boolean;
  command?: string;
};

export type TopicEntry = {
  key: string;
  topic: string;
  kind: string;
  bridge_present: boolean;
  runtime_status: "ok" | "failed" | "pending";
  runtime_detail?: string | null;
  confirmed: boolean;
  echo_command: string;
};

export type TopicsBundle = {
  project: string;
  topics: TopicEntry[];
  confirmed_topics: string[];
  bridge_topic_count: number;
  observations_path: string;
  command?: string;
};

export type TopicEchoSample = {
  ok: boolean;
  snippet: string;
  text: string;
  updated_at: string;
};

export type TopicWatchStatus = {
  project: string;
  state: "idle" | "running";
  topics: string[];
  latest: Record<string, TopicEchoSample>;
  command?: string;
};

export type ActionScaleEntry = {
  joint: string;
  action_scale: number;
  default_position: number;
};

export type ObservationScaleEntry = {
  id: string;
  key: string;
  topic: string;
  scale: number;
  offset: number;
  clip_min?: number | null;
  clip_max?: number | null;
  enabled: boolean;
};

export type TerminationSummary = {
  stage_name?: string | null;
  max_episode_steps: number;
  fall_base_height_threshold: number;
  max_tilt_rad: number;
  enabled_term_ids: string[];
};

export type TrainingConfig = {
  project: string;
  gains_path: string;
  rl_config_path: string;
  action_scales: ActionScaleEntry[];
  observation_scales: ObservationScaleEntry[];
  terminations: TerminationSummary[];
  curriculum_enabled: boolean;
  command?: string;
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
