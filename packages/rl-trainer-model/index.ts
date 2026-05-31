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
  ramUsedGb: number;
  ramTotalMb?: number;
  ramUsedMb?: number;
  ramAvailableMb?: number;
  gpuAvailable: boolean;
  gpuName: string;
  vramGb: number;
  profiledAt: string;
}

export interface RamMemorySample {
  ramTotalGb: number;
  ramUsedGb: number;
  ramAvailableGb: number;
  ramTotalMb: number;
  ramUsedMb: number;
  ramAvailableMb: number;
  sampledAt: string;
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
  /** Per-field enable flags (dot keys e.g. command.target_lin_vel_x). Omitted = enabled. */
  paramEnabled?: Record<string, boolean>;
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

export const STAGE_PARAM_HINTS: Record<string, string> = {
  "identity.name": "Human-readable stage label shown in the curriculum pipeline.",
  "identity.description": "Short note describing what this stage teaches.",
  "identity.gait_type": "Gait library entry linked to this stage (stand, walk, trot, …).",
  "identity.timesteps": "PPO environment steps to train before advancing or finishing this stage.",
  "command.target_lin_vel_x": "Commanded forward body velocity (m/s) the policy should track.",
  "command.target_lin_vel_y": "Commanded lateral velocity (m/s); usually 0 for straight locomotion.",
  "command.target_ang_vel_z": "Commanded yaw rate (rad/s) for turning behavior.",
  "command.target_body_height": "Target base height (m) during the stage.",
  "command.gait_speed_scale": "Multiplier on gait cycle speed; higher = faster footfall timing.",
  "disturbance.enabled": "Master switch for pushes, terrain roughness, and orientation noise.",
  "disturbance.push_force_n": "Periodic push magnitude applied to the base (Newtons).",
  "disturbance.push_interval_steps": "Sim steps between random pushes.",
  "disturbance.terrain_roughness": "Ground unevenness scale (0 = flat, 1 = very rough).",
  "disturbance.lateral_impulse_n": "Side impulse strength for lateral stability training (N).",
  "disturbance.orientation_noise_rad": "Random orientation perturbation magnitude (radians).",
  "termination.max_episode_steps": "Maximum steps per episode before timeout.",
  "termination.fall_base_height_threshold": "End episode if base drops below this height (m).",
  "termination.max_tilt_rad": "Maximum body tilt from upright (rad) before failure.",
  "termination.max_joint_torque": "Optional torque limit (N·m); 0 disables this check.",
  "termination.timeout_truncation": "Treat max-step timeout as truncation (not failure) for the learner.",
  "advance.min_mean_episode_reward": "Rolling mean reward required to auto-advance to the next stage.",
  "advance.min_episode_length_frac": "Mean episode length as a fraction of max_episode_steps.",
  "advance.max_fall_rate": "Maximum allowed fraction of episodes ending in a fall.",
};

export const REWARD_PARAM_HINTS: Record<string, string> = {
  weight: "Scale this term in the total reward sum.",
  target_lin_vel_x: "Velocity reward target for forward speed (m/s).",
  target_ang_vel_z: "Velocity reward target for yaw rate (rad/s).",
  target_height: "Desired base height (m) for height tracking rewards.",
  sigma: "Tracking tolerance — smaller = stricter, larger = more forgiving.",
  min_contacts: "Minimum feet on ground required for contact rewards.",
  max_impulse: "Foot impact threshold (N·s) for impact penalties.",
};

export const REWARD_TERM_HINTS: Record<string, string> = {
  lin_vel_tracking: "Reward matching commanded forward velocity.",
  ang_vel_tracking: "Reward matching commanded yaw rate.",
  base_height: "Reward maintaining target body height.",
  orientation_upright: "Reward keeping the body upright.",
  orientation_penalty: "Penalty for excessive body tilt.",
  velocity_penalty: "Penalty for unwanted base velocity (used in stand stages).",
  foot_contact: "Reward maintaining sufficient foot contacts.",
  torque_penalty: "Penalty for high joint torques (energy efficiency).",
  gait_symmetry: "Reward symmetric footfall timing across legs.",
  action_smoothness: "Penalty for abrupt action changes between steps.",
  impact_penalty: "Penalty for hard foot impacts.",
};

export function stageParamKey(section: string, name: string): string {
  return `${section}.${name}`;
}

export function rewardParamKey(termId: string, param: string): string {
  return `reward.${termId}.${param}`;
}

export function isStageParamEnabled(
  stage: Pick<CurriculumStage, "paramEnabled">,
  key: string,
  fallback = true
): boolean {
  const flags = stage.paramEnabled;
  if (!flags || !(key in flags)) return fallback;
  return Boolean(flags[key]);
}

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
