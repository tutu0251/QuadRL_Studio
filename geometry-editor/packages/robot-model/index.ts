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
  ixx: number;
  iyy: number;
  izz: number;
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

export interface MeasurementResult {
  tool: string;
  value: number;
  unit: string;
  label: string;
  points: Vec3[];
}

export type Selection =
  | { kind: "link"; id: string }
  | { kind: "joint"; id: string }
  | { kind: "shape"; linkId: string; shapeId: string }
  | null;

export type GizmoMode = "translate" | "rotate" | "scale";
export type GizmoTarget = "link" | "joint" | "shape";

export interface TemplateInfo {
  id: string;
  name: string;
  jointCount: number;
  category: string;
  description?: string;
}

/** Tooltip descriptions for geometry editor parameters. */
export const ROBOT_PARAM_HINTS: Record<string, string> = {
  mass: "Link mass in kilograms (SI).",
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
