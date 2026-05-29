/** Shared robot model types (geometry + physics editors). SI units: kg, m, N·m. */

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface Quat {
  x: number;
  y: number;
  z: number;
  w: number;
}

export interface Inertial {
  mass: number;
  com: Vec3;
  /** Inertial frame orientation relative to link (URDF inertial origin rpy as quat). */
  comRotation: Quat;
  ixx: number;
  ixy: number;
  ixz: number;
  iyy: number;
  iyz: number;
  izz: number;
}

export interface CollisionFriction {
  mu: number;
  mu2: number;
  kp: number;
  kd: number;
  /** Export any collision friction for this link. */
  enabled: boolean;
  useMu: boolean;
  useMu2: boolean;
  useKp: boolean;
  useKd: boolean;
}

export interface JointDynamics {
  damping: number;
  friction: number;
  effort: number;
  velocity: number;
}

export interface PrimitiveShape {
  id: string;
  type: "box" | "cylinder" | "sphere" | "capsule";
  dimensions: number[];
  localPosition: Vec3;
  localRotation: Quat;
  color: string;
  material: string;
}

export interface Link {
  id: string;
  name: string;
  parentJointId?: string | null;
  shapes: PrimitiveShape[];
  frame: { position: Vec3; rotation: Quat };
  inertial: Inertial;
  friction: CollisionFriction;
  /** Mark foot links for friction validation. */
  isFoot: boolean;
}

export interface Joint {
  id: string;
  name: string;
  parentLinkId: string;
  childLinkId: string;
  type: "fixed" | "revolute" | "continuous" | "prismatic";
  originPosition: Vec3;
  originRotation: Quat;
  axis: Vec3;
  lowerLimit: number;
  upperLimit: number;
  defaultValue: number;
  dynamics: JointDynamics;
}

export interface Pose {
  id: string;
  name: string;
  jointValues: Record<string, number>;
}

export type NamingConvention = "ROS2_UPPER" | "LOWER";

export interface RobotModel {
  id: string;
  name: string;
  version: string;
  links: Link[];
  joints: Joint[];
  poses: Pose[];
  templates: string[];
  namingConvention: NamingConvention;
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

export type Selection = { kind: "link"; id: string } | null;

export interface TemplateInfo {
  id: string;
  name: string;
  jointCount: number;
  category: string;
  description?: string;
}

export const defaultInertial = (): Inertial => ({
  mass: 1.0,
  com: { x: 0, y: 0, z: 0 },
  comRotation: { x: 0, y: 0, z: 0, w: 1 },
  ixx: 0.01,
  ixy: 0,
  ixz: 0,
  iyy: 0.01,
  iyz: 0,
  izz: 0.01,
});

export const defaultFriction = (): CollisionFriction => ({
  mu: 1.0,
  mu2: 1.0,
  kp: 1e6,
  kd: 1.0,
  enabled: false,
  useMu: true,
  useMu2: true,
  useKp: false,
  useKd: false,
});

export const defaultJointDynamics = (): JointDynamics => ({
  damping: 0.0,
  friction: 0.0,
  effort: 100.0,
  velocity: 10.0,
});
