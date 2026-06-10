/** Data shapes mirroring the Training Predictor backend (see backend/api + backend/tuner). */

export type StudyState = "pending" | "running" | "complete" | "stopped" | "error";

/** A sampled parameter value — namespaced hp.* / rw.* / rp.*.* on the wire. */
export type ParamValue = number | string;

export interface BestTrial {
  number: number;
  value: number;
  params: Record<string, ParamValue>;
}

/** One ParamSpec snapshot from the live search space. */
export interface SearchSpec {
  name: string;
  group: "hyperparam" | "reward_weight" | "reward_param" | string;
  kind: "float" | "int" | "categorical" | string;
  low: number | null;
  high: number | null;
  log: boolean;
  choices: ParamValue[] | null;
  fixed: ParamValue | null;
}

export interface DecisionChange {
  name: string;
  before: Partial<SearchSpec>;
  after: Partial<SearchSpec>;
}

/** A Claude advisor decision applied after a batch of trials. */
export interface Decision {
  action: string;
  rationale: string;
  stop: boolean;
  changes: DecisionChange[];
  after_trial: number;
  timestamp: string;
}

export type TuningMode = "global" | "sequential_stage";

/** One stage's tuning result in sequential mode. */
export interface StageResult {
  stage_index: number;
  stage_id: string;
  stage_name: string;
  status: "pending" | "running" | "done" | "stopped" | "failed" | string;
  n_completed: number;
  best_value: number | null;
  best_params: Record<string, ParamValue>;
  seed_checkpoint: string | null;
  decisions: Decision[];
}

export interface StudyStatus {
  status: StudyState;
  error: string | null;
  project: string;
  study_name: string;
  n_trials: number;
  n_completed: number;
  advisor_every_n: number;
  mock_objective: boolean;
  best: BestTrial | null;
  decisions: Decision[];
  search_space: SearchSpec[];
  // ---- sequential_stage mode (optional; present only when mode === "sequential_stage") ----
  mode?: TuningMode;
  current_stage_index?: number | null;
  total_stages?: number;
  stages_to_tune?: number[];
  trials_per_stage?: number;
  stages?: StageResult[];
}

/** Summary of a past per-stage sequence you can resume. */
export interface SequenceSummary {
  seq_name: string;
  stages_tuned: number;
  stages_done: number;
  stages_to_tune: number[];
}

export interface TrialRow {
  number: number;
  value: number | null;
  state: string;
  params: Record<string, ParamValue>;
}

/** A curriculum stage, named for human selection. */
export interface Stage {
  id: string;
  name: string;
  order: number;
  timesteps: number | null;
}

export interface StagesResponse {
  enabled: boolean;
  stages: Stage[];
}

/** Summary of a past tuning study you can resume. */
export interface StudySummary {
  study_name: string;
  n_trials: number;
  best_value: number | null;
  datetime_start: string | null;
}

export interface Health {
  status: string;
  editor: string;
  projects_root: string;
  advisor_key: boolean;
  advisor_backend: string;
  advisor_detail: string;
  monitor_url: string;
  monitor_reachable: boolean;
}

/** The tuning request — the camel-free wire contract the backend's StartTuningRequest expects. */
export interface StartRequest {
  project: string;
  /** "global" = one shared param set; "sequential_stage" = a sub-study per curriculum stage. */
  mode: TuningMode;
  /** Resume this existing study/sequence by name; null ⇒ start fresh. */
  study_name: string | null;
  n_trials: number;
  advisor_every_n: number;
  trial_timesteps: number;
  gazebo_headless: boolean;
  max_stages: number | null;
  monitor_base_url: string | null;
  mock_objective: boolean;
  include_hyperparams: boolean;
  include_reward_weights: boolean;
  include_reward_params: boolean;
  trial_timeout: number | null;
  // ---- sequential_stage mode ----
  trials_per_stage: number;
  timesteps_per_stage: number;
  stages_to_tune: number[] | null;
}

export interface StartResponse {
  task_id: string;
  study_name: string;
}

export interface StageApplySummary {
  id: string;
  name: string;
  reward_weights: Record<string, number>;
  reward_params: Record<string, Record<string, ParamValue>>;
}

export interface ApplyResult {
  ok: boolean;
  mode?: TuningMode;
  applied_from_trial?: number;
  project: string;
  hyperparameters?: Record<string, ParamValue>;
  reward_weights?: Record<string, number>;
  reward_params?: Record<string, Record<string, ParamValue>>;
  // sequential_stage: per-stage summary keyed by stage index
  stages?: Record<string, StageApplySummary>;
  files: string[];
  backups: string[];
}

export interface LogEntry {
  level: string;
  message: string;
}
