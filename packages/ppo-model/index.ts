/** PPO planner types — stable-baselines3-compatible hyperparameters. */

export type ComputeDevice = "auto" | "cpu" | "cuda";

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
  numEnvs: number;
  device: ComputeDevice;
}

export interface PpoPlannerModel {
  id: string;
  projectName: string;
  robotName: string;
  version: string;
  params: PpoHyperparams;
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

export const PPO_PARAM_GROUPS: { id: string; label: string; keys: (keyof PpoHyperparams)[] }[] = [
  { id: "rollout", label: "Rollout & batch", keys: ["nSteps", "batchSize", "nEpochs", "numEnvs"] },
  { id: "optimizer", label: "Optimizer", keys: ["learningRate", "maxGradNorm"] },
  { id: "rl", label: "RL objective", keys: ["gamma", "gaeLambda", "clipRange", "entCoef", "vfCoef"] },
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
  numEnvs: "Parallel training environments",
  device: "auto prefers CUDA when available",
};
