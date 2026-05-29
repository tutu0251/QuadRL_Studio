/** Sensor editor types — SI units, angles in rad. */

export type SimTarget = "gz_fortress";
export type SensorKind = "imu" | "contact" | "lidar";

export interface SensorPose {
  xyz: [number, number, number];
  rpy: [number, number, number];
}

export interface ImuConfig {
  enableOrientation: boolean;
}

export interface ContactConfig {
  collisionName: string;
}

export interface LidarConfig {
  samples: number;
  minRange: number;
  maxRange: number;
  horizontalFov: number;
  verticalSamples: number;
}

export interface SensorInstance {
  id: string;
  kind: SensorKind;
  name: string;
  parentLink: string;
  enabled: boolean;
  pose: SensorPose;
  rosTopic: string;
  updateRate: number;
  imu?: ImuConfig;
  contact?: ContactConfig;
  lidar?: LidarConfig;
}

export interface SensorModel {
  id: string;
  projectName: string;
  robotName: string;
  version: string;
  sourceCtrlUrdf: string;
  simTarget: SimTarget;
  topicPrefix: string;
  gzModelName: string;
  updateRateDefault: number;
  linkNames: string[];
  sensors: SensorInstance[];
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

export type Selection =
  | { kind: "link"; name: string }
  | { kind: "sensor"; id: string }
  | null;

export const SENSOR_KIND_LABELS: Record<SensorKind, string> = {
  imu: "IMU",
  contact: "Contact",
  lidar: "Lidar",
};

export const DEFAULT_IMU: ImuConfig = { enableOrientation: true };
export const DEFAULT_CONTACT: ContactConfig = { collisionName: "collision" };
export const DEFAULT_LIDAR: LidarConfig = {
  samples: 360,
  minRange: 0.1,
  maxRange: 30.0,
  horizontalFov: 6.28318,
  verticalSamples: 1,
};
