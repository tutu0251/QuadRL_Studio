import * as THREE from "three";
import type { MeasurementResult, RobotModel } from "@robot-model";
import {
  computeJointWorldTransforms,
  computeLinkWorldTransforms,
  computeVisualGroundOffset,
} from "./kinematics";

/** Lowest world-space Z of all shape geometry (matches viewport grounding). */
export function computeGeometryMinZ(model: RobotModel): number {
  const offset = computeVisualGroundOffset(model);
  return offset === 0 ? 0 : -offset;
}

function toVec3(v: THREE.Vector3) {
  return { x: v.x, y: v.y, z: v.z };
}

export function measureDistance(
  model: RobotModel,
  linkAId: string,
  linkBId: string
): MeasurementResult | null {
  const tf = computeLinkWorldTransforms(model);
  const a = tf.get(linkAId);
  const b = tf.get(linkBId);
  if (!a || !b) return null;
  const d = a.position.distanceTo(b.position);
  return {
    tool: "distance",
    value: d,
    unit: "m",
    label: "Point-to-point",
    points: [toVec3(a.position), toVec3(b.position)],
  };
}

export function measureHeight(model: RobotModel, linkId: string): MeasurementResult | null {
  const tf = computeLinkWorldTransforms(model);
  const linkTf = tf.get(linkId);
  if (!linkTf) return null;
  const groundZ = computeGeometryMinZ(model);
  const p = linkTf.position;
  return {
    tool: "height",
    value: p.z - groundZ,
    unit: "m",
    label: "Height from ground",
    points: [{ x: p.x, y: p.y, z: groundZ }, toVec3(p)],
  };
}

export function measureLinkLength(model: RobotModel, childLinkId: string): MeasurementResult | null {
  const joint = model.joints.find((j) => j.childLinkId === childLinkId);
  if (!joint) return null;
  const jointTfs = computeJointWorldTransforms(model);
  const linkTfs = computeLinkWorldTransforms(model);
  const pa = jointTfs.get(joint.id);
  const pb = linkTfs.get(childLinkId);
  if (!pa || !pb) return null;
  const d = pa.position.distanceTo(pb.position);
  return {
    tool: "link_length",
    value: d,
    unit: "m",
    label: "Parent to child link",
    points: [toVec3(pa.position), toVec3(pb.position)],
  };
}

export function measureAngle(
  model: RobotModel,
  jointAId: string,
  jointBId: string
): MeasurementResult | null {
  const ja = model.joints.find((j) => j.id === jointAId);
  const jb = model.joints.find((j) => j.id === jointBId);
  if (!ja || !jb) return null;
  const ax = new THREE.Vector3(ja.axis.x, ja.axis.y, ja.axis.z).normalize();
  const bx = new THREE.Vector3(jb.axis.x, jb.axis.y, jb.axis.z).normalize();
  const angle = Math.acos(Math.max(-1, Math.min(1, ax.dot(bx))));
  return {
    tool: "angle",
    value: THREE.MathUtils.radToDeg(angle),
    unit: "deg",
    label: "Joint axis angle",
    points: [],
  };
}

export function measureLegReach(
  model: RobotModel,
  hipLinkId: string,
  footLinkId: string
): MeasurementResult | null {
  return measureDistance(model, hipLinkId, footLinkId);
}
