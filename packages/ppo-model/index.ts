/** PPO planner types — stable-baselines3-compatible hyperparameters. */

export type ComputeDevice = "auto" | "cpu" | "cuda";
export type VecEnvType = "dummy" | "subproc";
/** Policy/value MLP size preset; resolved to an SB3 net_arch list on export. */
export type NetArchPreset = "small" | "medium" | "large";
export type CheckpointFrequency = "end_only" | "steps" | "rollout";
export type BestModelMetric =
  | "mean_episode_reward"
  | "mean_episode_length"
  | "rolling_mean_reward";
export type BestModelMode = "max" | "min";
export type ExportConfigFormat = "yaml" | "json" | "json_min" | "toml";

export interface MachineProfile {
  hostname: string;
  platform: string;
  cpuCountLogical: number;
  cpuCountPhysical: number;
  ramGb: number;
  gpuAvailable: boolean;
  gpuName: string;
  vramGb: number;
  profiledAt: string;
}

export interface PpoHyperparams {
  learningRate: number;
  nSteps: number;
  batchSize: number;
  nEpochs: number;
  gamma: number;
  gaeLambda: number;
  clipRange: number;
  entCoef: number;
  vfCoef: number;
  maxGradNorm: number;
  totalTimesteps: number;
  device: ComputeDevice;
  netArch: NetArchPreset;
  logStdInit: number;
}

/** Preset → SB3 net_arch (shared pi/vf hidden layer sizes). */
export const NET_ARCH_PRESETS: Record<NetArchPreset, number[]> = {
  small: [64, 64],
  medium: [256, 256],
  large: [512, 256],
};

export const NET_ARCH_LABELS: Record<NetArchPreset, string> = {
  small: "Small — 64 × 64",
  medium: "Medium — 256 × 256",
  large: "Large — 512 × 256",
};

export interface ParallelConfig {
  numEnvs: number;
  vecEnvType: VecEnvType;
  nProc: number | null;
}

export interface CheckpointConfig {
  enabled: boolean;
  directory: string;
  frequency: CheckpointFrequency;
  frequencySteps: number;
  keepLastN: number;
  filenameTemplate: string;
  saveOnInterrupt: boolean;
}

export interface BestModelConfig {
  enabled: boolean;
  metric: BestModelMetric;
  mode: BestModelMode;
  directory: string;
  filename: string;
  minImprovement: number;
}

export interface ExportFormatConfig {
  formats: ExportConfigFormat[];
  includeMachineProfile: boolean;
  includeRecommendationNotes: boolean;
  includeHeaderComments: boolean;
  sortKeys: boolean;
}

export interface PpoPlannerModel {
  id: string;
  projectName: string;
  robotName: string;
  version: string;
  params: PpoHyperparams;
  parallel: ParallelConfig;
  checkpoint: CheckpointConfig;
  bestModel: BestModelConfig;
  exportFormat: ExportFormatConfig;
  useRecommended: boolean;
  machineProfile: MachineProfile | null;
  recommendationNotes: string[];
  metadata: Record<string, unknown>;
}

export interface ValidationIssue {
  severity: string;
  code: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export type OutputPatch = {
  checkpoint?: Partial<CheckpointConfig>;
  bestModel?: Partial<BestModelConfig>;
  exportFormat?: Partial<ExportFormatConfig>;
};

export const EXPORT_FORMAT_OPTIONS: {
  id: ExportConfigFormat;
  label: string;
  filenameSuffix: string;
  description: string;
}[] = [
  {
    id: "yaml",
    label: "YAML",
    filenameSuffix: "_config.yaml",
    description: "Default for training launcher and human editing",
  },
  {
    id: "json",
    label: "JSON",
    filenameSuffix: "_config.json",
    description: "Pretty-printed JSON for tooling and CI",
  },
  {
    id: "json_min",
    label: "JSON (minified)",
    filenameSuffix: "_config.min.json",
    description: "Compact JSON without extra whitespace",
  },
  {
    id: "toml",
    label: "TOML",
    filenameSuffix: "_config.toml",
    description: "TOML tables for Rust/Python TOML consumers",
  },
];

export const PPO_PARAM_GROUPS: { id: string; label: string; keys: (keyof PpoHyperparams)[] }[] = [
  { id: "rollout", label: "Rollout & batch", keys: ["nSteps", "batchSize", "nEpochs"] },
  { id: "optimizer", label: "Optimizer", keys: ["learningRate", "maxGradNorm"] },
  { id: "rl", label: "RL objective", keys: ["gamma", "gaeLambda", "clipRange", "entCoef", "vfCoef"] },
  { id: "policy", label: "Policy architecture", keys: ["netArch", "logStdInit"] },
  { id: "training", label: "Training run", keys: ["totalTimesteps", "device"] },
];

export const PPO_PARAM_HINTS: Partial<Record<keyof PpoHyperparams, string>> = {
  learningRate: "Adam learning rate",
  nSteps: "Steps per env before each PPO update",
  batchSize: "Minibatch size (should divide n_steps × num_envs)",
  nEpochs: "Epochs over rollout data per update",
  gamma: "Discount factor",
  gaeLambda: "GAE λ",
  clipRange: "PPO clip range ε",
  entCoef: "Entropy bonus coefficient",
  vfCoef: "Value-function loss coefficient",
  maxGradNorm: "Gradient clipping max norm",
  totalTimesteps: "Total environment steps for training",
  device: "auto prefers CUDA when available",
  netArch: "Policy/value MLP hidden layers (shared pi/vf)",
  logStdInit: "Initial action log-std; lower = less exploration noise (exp(−1)=0.37)",
};

export const PARALLEL_HINTS: Record<keyof ParallelConfig, string> = {
  numEnvs: "Parallel training environments (rollout = n_steps × num_envs)",
  vecEnvType: "subproc spawns worker processes; dummy runs envs in-process",
  nProc: "Worker processes for subproc vec env (≤ num_envs and CPU cores)",
};

export const CHECKPOINT_HINTS: Record<keyof CheckpointConfig, string> = {
  enabled: "Write SB3 .zip checkpoints during training",
  directory: "Folder under the project root (relative path)",
  frequency: "When to save: end only, every N steps, or each rollout",
  frequencySteps: "Step interval when frequency is steps",
  keepLastN: "Rotate checkpoints; 0 keeps all",
  filenameTemplate: "Use {stage_id} for curriculum stage id",
  saveOnInterrupt: "Attempt save when training is interrupted",
};

export const BEST_MODEL_HINTS: Record<keyof BestModelConfig, string> = {
  enabled: "Track and copy the best-performing checkpoint",
  metric: "TensorBoard / eval metric to optimize",
  mode: "max for reward; min for length or cost",
  directory: "Folder for best_model.zip (relative path)",
  filename: "Base name without extension",
  minImprovement: "Minimum delta required to replace best",
};

export const EXPORT_HINTS: Omit<Record<keyof ExportFormatConfig, string>, "formats"> & {
  formats: string;
} = {
  formats: "One or more files written on export (select all that apply)",
  includeMachineProfile: "Embed host profile in exported config",
  includeRecommendationNotes: "Embed recommendation notes from Recommend",
  includeHeaderComments: "Add generator header (YAML/TOML # or JSON //)",
  sortKeys: "Alphabetize keys in exported file",
};

export const CHECKPOINT_FREQUENCY_LABELS: Record<CheckpointFrequency, string> = {
  end_only: "End of training",
  steps: "Every N steps",
  rollout: "Each rollout (n_steps × num_envs)",
};

export const BEST_MODEL_METRIC_LABELS: Record<BestModelMetric, string> = {
  mean_episode_reward: "Mean episode reward",
  mean_episode_length: "Mean episode length",
  rolling_mean_reward: "Rolling mean reward",
};
