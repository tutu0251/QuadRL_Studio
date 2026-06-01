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

export interface TerminationTerm {
  id: string;
  category: string;
  enabled: boolean;
  params: Record<string, number>;
}

export interface TerminationConfig {
  maxEpisodeSteps: number;
  fallBaseHeightThreshold: number;
  maxTiltRad: number;
  maxJointTorque: number | null;
  timeoutTruncation: boolean;
  terminationTerms: TerminationTerm[];
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
  /** Selected gate types for this stage (multi-select). */
  gaitTypeIds: string[];
  /** @deprecated Legacy single selection; migrated to gaitTypeIds on load. */
  gaitTypeId?: string;
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

export const GAIT_CATALOG_IDS = ["none", "walk", "trot", "gallop"] as const;

export type GaitCatalogId = (typeof GAIT_CATALOG_IDS)[number];

export const CURRICULUM_CATALOG: CurriculumInfo[] = [
  {
    id: "stand_sprint",
    name: "Stand → Sprint (flat)",
    description: "Four gate types from none through gallop on flat terrain.",
    stageCount: 4,
    totalTimesteps: 2_100_000,
    terrainProfile: "flat",
  },
  {
    id: "stand_sprint_rough",
    name: "Stand → Sprint (rough terrain)",
    description: "Same gate-type progression with disturbances and rough terrain.",
    stageCount: 4,
    totalTimesteps: 2_310_000,
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
    description: "Track commanded velocity with posture and energy penalties.",
    difficulty: "beginner",
  },
  {
    id: "stand_still",
    name: "Stand still",
    description: "Balance in place with survival, height, and velocity penalties.",
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
    description: "Full reward/penalty catalog — enable terms manually.",
    difficulty: "advanced",
  },
];

export * from "./rewardCatalog";
export * from "./terminationCatalog";

export const REWARD_CATEGORY_HINTS: Record<string, string> = {
  velocity: "Requires base linear/angular velocity observations",
  orientation: "Requires IMU orientation or equivalent",
  energy: "Uses joint torques / effort",
  contact: "Requires foot contact sensors",
  action_smoothness: "Penalizes action deltas",
  height: "Base height tracking",
  posture: "Body orientation / joint pose relative to nominal",
  gait: "Footfall timing, clearance, and diagonal pairing",
  survival: "Per-step alive bonus",
  tracking: "Deviation from commanded reference trajectories",
  stability: "ZMP / support polygon margins",
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
  "identity.gait_type": "Gate types for this stage — select one or more (none, walk, trot, gallop).",
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

export const TERMINATION_CATEGORY_HINTS: Record<string, string> = {
  contact: "Requires foot contact and slip observations",
  velocity: "Uses base linear/angular velocity",
  safety: "Joint limit proximity and self-collision checks",
  energy: "Joint torques and power draw",
  height: "Base height vs command and terrain foot contacts",
  monitoring: "Episode reward statistics for runaway policies",
};

export const TERMINATION_PARAM_HINTS: Record<string, string> = {
  slip_threshold: "Foot slip speed (m/s) above which the episode fails.",
  min_contacts: "Minimum feet on ground required to avoid contact-loss failure.",
  contact_loss_steps: "Consecutive steps below min_contacts before termination.",
  max_lin_vel: "Maximum allowed base linear speed (m/s).",
  max_ang_vel: "Maximum allowed base angular speed (rad/s).",
  limit_margin: "Radians from hard joint limits before failure.",
  max_joint_torque: "Per-joint torque ceiling (N·m).",
  max_joint_power: "Aggregate joint power ceiling (W).",
  max_height_deviation: "Allowed |base height − commanded height| (m).",
  min_terrain_contacts: "Minimum feet touching terrain/ground.",
  max_step_reward: "Single-step reward above which the episode is flagged.",
  cumulative_threshold: "Rolling cumulative reward spike threshold.",
};

export const TERMINATION_TERM_HINTS: Record<string, string> = {
  foot_slip_contact_loss: "End episode on excessive foot slip or sustained loss of contacts.",
  base_linear_velocity_limit: "End episode if base linear velocity exceeds limit.",
  base_angular_velocity_limit: "End episode if base angular velocity exceeds limit.",
  joint_limits_self_collision: "End episode near joint limits or on self-collision.",
  energy_torque_safety: "End episode when torques or power exceed safe bounds.",
  height_deviation_terrain_contact: "End episode on large height error or missing terrain contact.",
  reward_anomaly: "End episode on abnormal per-step or cumulative reward spikes.",
};

export const REWARD_PARAM_HINTS: Record<string, string> = {
  weight: "Scale this term in the total reward sum (recommended value shown in catalog).",
  target_height: "Desired base height (m); auto-synced from stage command on recommend.",
  sigma: "Tracking tolerance — smaller = stricter, larger = more forgiving.",
  min_contacts: "Minimum feet on ground required for contact rewards.",
  target_air_time: "Desired swing-phase duration (s) per foot.",
  min_clearance: "Minimum foot height during swing (m).",
  max_switches_per_step: "Max allowed contact state changes per step.",
  threshold: "Impact or slip magnitude threshold before penalty applies.",
  margin: "ZMP margin inside support polygon (m).",
};

export const REWARD_TERM_HINTS: Record<string, string> = {
  alive: "Per-step survival bonus while the episode continues.",
  upright: "Reward keeping the body upright (roll/pitch near zero).",
  height: "Reward maintaining target body height.",
  posture: "Reward matching nominal standing posture.",
  contact: "Reward maintaining sufficient foot contacts.",
  forward_tracking: "Reward matching commanded forward velocity.",
  lateral_tracking: "Reward matching commanded lateral velocity.",
  yaw_tracking: "Reward matching commanded yaw rate.",
  diagonal_balance: "Reward symmetric diagonal footfall timing (trot-like gait).",
  air_time: "Reward swing-phase duration near target.",
  foot_clearance: "Reward lifting feet above minimum clearance in swing.",
  angular_velocity: "Penalty for excessive base angular velocity.",
  linear_velocity: "Penalty for unwanted horizontal base velocity (stand stages).",
  z_velocity: "Penalty for vertical base velocity / bouncing.",
  joint_velocity: "Penalty for high joint velocities (energy).",
  action_velocity: "Penalty for large action magnitudes.",
  action_rate: "Penalty for rapid action changes between steps.",
  posture_penalty: "Penalty for deviating from upright nominal pose.",
  target_posture: "Penalty for deviating from commanded reference posture.",
  smoothness: "Penalty for non-smooth action trajectories.",
  contact_balance: "Penalty for uneven load across feet.",
  contact_switch: "Penalty for excessive foot contact toggling.",
  target_like: "Penalty for deviating from target-like reference motion.",
  stumble: "Penalty for hard foot impacts / tripping.",
  slip: "Penalty for foot slip relative to ground.",
  zmp: "Penalty when ZMP approaches support polygon edge.",
};

export function stageParamKey(section: string, name: string): string {
  return `${section}.${name}`;
}

export function rewardParamKey(termId: string, param: string): string {
  return `reward.${termId}.${param}`;
}

export function terminationParamKey(termId: string, param: string): string {
  return `termination.${termId}.${param}`;
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
