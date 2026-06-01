/** Sensor editor types — SI units, angles in rad. */

export type SimTarget = "gz_fortress";
export type SensorKind = "imu" | "contact" | "lidar" | "odom";

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

export interface OdomConfig {
  dimensions: number;
  odomFrame: string;
  robotBaseFrame: string;
  noiseStddev: number;
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
  odom?: OdomConfig;
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
  details?: Record<string, unknown>;
}

export type Selection =
  | { kind: "link"; name: string }
  | { kind: "sensor"; id: string }
  | null;

export const SENSOR_KIND_LABELS: Record<SensorKind, string> = {
  imu: "IMU",
  contact: "Contact",
  lidar: "Lidar",
  odom: "Odometry",
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
export const DEFAULT_ODOM: OdomConfig = {
  dimensions: 3,
  odomFrame: "",
  robotBaseFrame: "",
  noiseStddev: 0.0,
};

/** Tooltip descriptions for sensor editor parameters. */
export const SENSOR_PARAM_HINTS: Record<string, string> = {
  topicPrefix: "ROS 2 topic namespace prefix prepended to all sensor topics.",
  gzModelName: "Gazebo Sim model name used in topic paths and plugin configuration.",
  updateRateDefault: "Default publish rate (Hz) for newly added sensors.",
  enabled: "When off, the sensor is not exported to the sensor URDF/SDF.",
  parentLink: "URDF link the sensor is rigidly attached to.",
  rosTopic: "Full ROS 2 topic name for this sensor's messages.",
  updateRate: "Sensor publish rate (Hz) for this instance.",
  poseX: "Sensor position offset along link X (m).",
  poseY: "Sensor position offset along link Y (m).",
  poseZ: "Sensor position offset along link Z (m).",
  roll: "Sensor roll orientation offset relative to the link frame (rad).",
  pitch: "Sensor pitch orientation offset relative to the link frame (rad).",
  yaw: "Sensor yaw orientation offset relative to the link frame (rad).",
  enableOrientation: "Publish orientation quaternion from IMU (in addition to angular velocity).",
  collisionName: "Gazebo collision element name monitored by the contact sensor.",
  samples: "Number of horizontal lidar rays per scan.",
  minRange: "Minimum valid range measurement (m).",
  maxRange: "Maximum valid range measurement (m).",
  horizontalFov: "Horizontal field of view (rad); 2π = full circle.",
  verticalSamples: "Number of vertical lidar channels.",
  odomFrame: "Odometry parent frame ID (empty = auto from GZ model name).",
  robotBaseFrame: "Child base link frame for the odometry transform.",
  dimensions: "Odometry state dimensionality (2 = planar, 3 = full SE(2)/SE(3)).",
  noiseStddev: "Gaussian noise standard deviation added to odometry measurements.",
};
