/** RL Trainer types — SB3 + ROS2/Gazebo training config. */

export type RewardTermType = "reward" | "penalty";
export type CustomParamValue = number | string | boolean;
export type TerrainProfile = "flat" | "rough";

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

export interface GaitPhaseOffsets {
  fl: number;
  fr: number;
  rl: number;
  rr: number;
}

export interface GaitType {
  id: string;
  name: string;
  builtin: boolean;
  cycleTime: number;
  dutyFactor: number;
  phaseOffsets: GaitPhaseOffsets;
  swingHeight?: number;
  stepLength?: number;
  bodyHeight?: number;
}

export interface StageCommand {
  targetLinVelX: number;
  targetLinVelY: number;
  targetAngVelZ: number;
  targetBodyHeight: number;
  gaitSpeedScale: number;
}

export interface DisturbanceConfig {
  enabled: boolean;
  pushForceN: number;
  pushIntervalSteps: number;
  terrainRoughness: number;
  lateralImpulseN: number;
  randomOrientationNoiseRad: number;
}

export interface CurriculumStage {
  id: string;
  name: string;
  order: number;
  description: string;
  timesteps: number;
  targetLinVelX: number;
  targetAngVelZ: number;
  gaitTypeId: string;
  command: StageCommand;
  disturbance: DisturbanceConfig;
  rewardTerms: RewardTerm[];
  termination: TerminationConfig;
  advanceCriteria: CurriculumAdvanceCriteria;
}

export interface CurriculumConfig {
  enabled: boolean;
  curriculumId: string | null;
  name: string;
  description: string;
  terrainProfile: TerrainProfile;
  stages: CurriculumStage[];
  currentStageIndex: number;
  loadPreviousCheckpoint: boolean;
  resetPolicyOnStageAdvance: boolean;
}

export interface CurriculumEntry {
  id: string;
  name: string;
  description: string;
  terrainProfile: TerrainProfile;
  stages: CurriculumStage[];
  loadPreviousCheckpoint: boolean;
  resetPolicyOnStageAdvance: boolean;
}

export interface TrainingCheckpointConfig {
  resumeCheckpointPath: string | null;
  checkpointDirectory: string;
}

export interface CheckpointInfo {
  path: string;
  filename: string;
  sizeBytes: number;
  modifiedAt: string;
}

export interface CurriculumInfo {
  id: string;
  name: string;
  description: string;
  stageCount: number;
  totalTimesteps: number;
  terrainProfile: TerrainProfile;
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
  gaitTypes: GaitType[];
  curriculumLibrary: CurriculumEntry[];
  activeCurriculumId: string | null;
  trainingCheckpoint: TrainingCheckpointConfig;
  useRecommended: boolean;
  customParams: Record<string, CustomParamValue>;
  metadata: Record<string, unknown>;
}

export const GAIT_CATALOG_IDS = [
  "stand",
  "recover",
  "walk",
  "trot",
  "pace",
  "bound",
  "gallop",
] as const;

export type GaitCatalogId = (typeof GAIT_CATALOG_IDS)[number];

export const CURRICULUM_CATALOG: CurriculumInfo[] = [
  {
    id: "stand_sprint",
    name: "Stand → Sprint (flat)",
    description: "Seven gait stages from stand through gallop on flat terrain.",
    stageCount: 7,
    totalTimesteps: 3_500_000,
    terrainProfile: "flat",
  },
  {
    id: "stand_sprint_rough",
    name: "Stand → Sprint (rough terrain)",
    description: "Same gait progression with disturbances and rough terrain.",
    stageCount: 7,
    totalTimesteps: 3_850_000,
    terrainProfile: "rough",
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

export const GAIT_PARAM_HINTS: Record<string, string> = {
  cycleTime: "Full gait cycle duration in seconds",
  dutyFactor: "Stance phase fraction (0–1)",
  swingHeight: "Foot clearance during swing phase (m)",
  stepLength: "Nominal step length (m)",
  bodyHeight: "Target body height (m)",
};

export function defaultStageCommand(linX = 0, angZ = 0): StageCommand {
  return {
    targetLinVelX: linX,
    targetLinVelY: 0,
    targetAngVelZ: angZ,
    targetBodyHeight: 0.35,
    gaitSpeedScale: 1,
  };
}

export function defaultDisturbance(rough = false): DisturbanceConfig {
  return {
    enabled: rough,
    pushForceN: rough ? 25 : 0,
    pushIntervalSteps: rough ? 500 : 0,
    terrainRoughness: rough ? 0.3 : 0,
    lateralImpulseN: rough ? 10 : 0,
    randomOrientationNoiseRad: rough ? 0.05 : 0,
  };
}

export function defaultTrainingCheckpoint(): TrainingCheckpointConfig {
  return {
    resumeCheckpointPath: null,
    checkpointDirectory: "checkpoints",
  };
}
