/** Control editor types — SI units, joint angles in rad unless noted. */

export type TrainingProfile = "ProfileA" | "ProfileB" | "ProfileC";

/** ros2_control simulation controller for ProfileA position control. */
export const DEFAULT_SIM_CONTROLLER = "joint_trajectory_controller";

export const SIM_CONTROLLER_LABELS: Record<string, string> = {
  joint_trajectory_controller: "Joint Trajectory Controller",
  forward_command_controller: "Forward Command Controller (legacy)",
};

/** Gazebo Fortress + ROS 2 Humble gz_ros2_control defaults. */
export const DEFAULT_SIM_PLUGIN = "gz_ros2_control";
export const DEFAULT_HARDWARE_PLUGIN = "gz_ros2_control/GazeboSimSystem";
export const DEFAULT_SIM_PLUGIN_FILENAME = "libgz_ros2_control-system.so";
export const DEFAULT_SIM_PLUGIN_CLASS =
  "gz_ros2_control::GazeboSimROS2ControlPlugin";

export interface JointControlConfig {
  name: string;
  type: "revolute" | "prismatic" | "continuous";
  childLinkName: string;
  lowerLimit: number;
  upperLimit: number;
  effort: number;
  velocity: number;
  commandInterface: string;
  stateInterfaces: string[];
  kp: number;
  kd: number;
  defaultPosition: number;
  actionScale: number;
  enabled: boolean;
  profileParams: Record<string, unknown>;
}

export interface ControlModel {
  id: string;
  projectName: string;
  robotName: string;
  version: string;
  sourceUrdf: string;
  trainingProfile: TrainingProfile;
  simPlugin: string;
  hardwarePlugin: string;
  simPluginFilename: string;
  simPluginClass: string;
  ros2Distro: string;
  controllerType: string;
  updateRate: number;
  actuatedJoints: JointControlConfig[];
  metadata: Record<string, unknown>;
}

export interface ValidationIssue {
  severity: string;
  code: string;
  message: string;
  entityType?: string;
  entityId?: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export type Selection = { kind: "joint"; name: string } | null;

export interface AsyncTaskStatus {
  task_id: string;
  status: string;
  logs: { timestamp: string; level: string; message: string }[];
  result?: Record<string, unknown>;
}

export const PROFILE_LABELS: Record<TrainingProfile, string> = {
  ProfileA: "Position control",
  ProfileB: "Reserved (not implemented)",
  ProfileC: "Reserved (not implemented)",
};

export const PROFILE_IMPLEMENTED: Record<TrainingProfile, boolean> = {
  ProfileA: true,
  ProfileB: false,
  ProfileC: false,
};
