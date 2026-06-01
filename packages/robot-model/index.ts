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

/** Tooltip descriptions for editable physics and geometry parameters. */
export const ROBOT_PARAM_HINTS: Record<string, string> = {
  mass: "Link mass in kilograms (SI).",
  density: "Material density (kg/m³) used to auto-estimate mass from collision geometry volume.",
  com: "Center of mass position relative to the link frame (m).",
  comX: "Center of mass offset along the link X axis (m).",
  comY: "Center of mass offset along the link Y axis (m).",
  comZ: "Center of mass offset along the link Z axis (m).",
  ixx: "Moment of inertia about the link X axis (kg·m²).",
  ixy: "Product of inertia Ixy (kg·m²); symmetric inertia tensor.",
  ixz: "Product of inertia Ixz (kg·m²); symmetric inertia tensor.",
  iyy: "Moment of inertia about the link Y axis (kg·m²).",
  iyz: "Product of inertia Iyz (kg·m²); symmetric inertia tensor.",
  izz: "Moment of inertia about the link Z axis (kg·m²).",
  mu: "Primary friction coefficient μ₁ for Gazebo contact.",
  mu2: "Secondary friction coefficient μ₂ (anisotropic friction).",
  frictionKp: "Contact stiffness kp (N/m); high values reduce penetration.",
  frictionKd: "Contact damping kd (N·s/m).",
  useCollisionFriction: "Export collision friction parameters for this link to Gazebo.",
  isFoot: "Mark as a foot link for locomotion friction validation.",
  damping: "Joint viscous damping coefficient.",
  jointFriction: "Joint Coulomb friction torque (N·m or N).",
  effort: "Maximum joint actuator effort/torque limit (N·m).",
  velocity: "Maximum joint velocity limit (rad/s or m/s).",
  position: "Translation offset in the parent or link frame (m).",
  rotation: "Orientation as Euler angles (degrees) in the parent or link frame.",
  scale: "Primitive dimensions — box W×H×D, cylinder/capsule radius×length (m).",
  defaultValue: "Default joint position at reset (rad or m).",
  lowerLimit: "Minimum joint angle or displacement (rad or m).",
  upperLimit: "Maximum joint angle or displacement (rad or m).",
  axis: "Joint rotation or translation axis unit vector in the joint frame.",
  jointType: "Kinematic joint type — revolute (1-DoF rotation), prismatic (1-DoF slide), etc.",
  parent: "Parent link or joint this entity attaches to in the kinematic tree.",
};
