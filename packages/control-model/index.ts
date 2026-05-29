/** Control editor types — SI units, joint angles in rad unless noted. */

export type TrainingProfile = "ProfileA" | "ProfileB" | "ProfileC";

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
