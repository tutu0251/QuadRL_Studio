/** RL Trainer types — SB3 + ROS2/Gazebo training config. */

export type RewardTermType = "reward" | "penalty";
export type CustomParamValue = number | string | boolean;

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

export interface RewardTerm {
  id: string;
  type: RewardTermType;
  category: string;
  weight: number;
  enabled: boolean;
  params: Record<string, number>;
}

export interface TerminationConfig {
  maxEpisodeSteps: number;
  fallBaseHeightThreshold: number;
  maxTiltRad: number;
  maxJointTorque: number | null;
  timeoutTruncation: boolean;
}

export interface CurriculumAdvanceCriteria {
  minMeanEpisodeReward: number;
  minEpisodeLengthFrac: number;
  maxFallRate: number;
  minTimestepsInStage: number | null;
}

export interface CurriculumStage {
  id: string;
  name: string;
  order: number;
  description: string;
  timesteps: number;
  targetLinVelX: number;
  targetAngVelZ: number;
  rewardTerms: RewardTerm[];
  termination: TerminationConfig;
  advanceCriteria: CurriculumAdvanceCriteria;
}

export interface CurriculumConfig {
  enabled: boolean;
  curriculumId: string | null;
  name: string;
  description: string;
  stages: CurriculumStage[];
  currentStageIndex: number;
  loadPreviousCheckpoint: boolean;
  resetPolicyOnStageAdvance: boolean;
}

export interface CurriculumInfo {
  id: string;
  name: string;
  description: string;
  stageCount: number;
  totalTimesteps: number;
}

export interface RlTrainerModel {
  id: string;
  projectName: string;
  robotName: string;
  version: string;
  selectedPresetId: string | null;
  recommendationNotes: string[];
  machineProfile: MachineProfile | null;
  rewardTerms: RewardTerm[];
  termination: TerminationConfig;
  curriculum: CurriculumConfig;
  customParams: Record<string, CustomParamValue>;
  metadata: Record<string, unknown>;
}

export const CURRICULUM_CATALOG: CurriculumInfo[] = [
  {
    id: "stand_to_sprint",
    name: "Stand still → Sprint",
    description: "Five stages: balance, slow walk, walk, run, sprint (2.1M steps).",
    stageCount: 5,
    totalTimesteps: 2_100_000,
  },
];

export interface PresetInfo {
  id: string;
  name: string;
  description: string;
  difficulty: "beginner" | "intermediate" | "advanced";
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

export const PRESET_CATALOG: PresetInfo[] = [
  {
    id: "velocity_tracking",
    name: "Velocity tracking",
    description: "Track commanded linear/angular velocity with orientation and torque penalties.",
    difficulty: "beginner",
  },
  {
    id: "stand_still",
    name: "Stand still",
    description: "Balance in place with height/orientation rewards and low velocity penalty.",
    difficulty: "beginner",
  },
  {
    id: "efficient_locomotion",
    name: "Efficient locomotion",
    description: "Velocity tracking with stronger energy and impact penalties.",
    difficulty: "intermediate",
  },
  {
    id: "custom_blank",
    name: "Custom (blank)",
    description: "Empty reward list — configure manually or via custom params.",
    difficulty: "advanced",
  },
];

export const REWARD_CATEGORY_HINTS: Record<string, string> = {
  velocity: "Requires base linear/angular velocity observations",
  orientation: "Requires IMU orientation or equivalent",
  energy: "Uses joint torques / effort",
  contact: "Requires foot contact sensors",
  action_smoothness: "Penalizes action deltas",
  height: "Base height tracking",
};
