/** Forward kinematics helpers for gizmo placement. */
import * as THREE from "three";
import type { Joint, Link, PrimitiveShape, Quat, RobotModel, Vec3 } from "@robot-model";
import { shapeVisualQuaternion } from "./primitiveVisual";

export interface Transform {
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
}

function v3(v: Vec3): THREE.Vector3 {
  return new THREE.Vector3(v.x, v.y, v.z);
}

function q4(q: Quat): THREE.Quaternion {
  return new THREE.Quaternion(q.x, q.y, q.z, q.w);
}

function compose(parent: Transform, pos: Vec3, rot: Quat): Transform {
  const p = v3(pos).applyQuaternion(parent.quaternion).add(parent.position);
  const r = parent.quaternion.clone().multiply(q4(rot));
  return { position: p, quaternion: r };
}

export function jointMotionQuat(joint: { type: string; axis: Vec3; defaultValue: number }): THREE.Quaternion {
  if (joint.type === "fixed" || joint.type === "prismatic") {
    return new THREE.Quaternion();
  }
  const axis = v3(joint.axis).normalize();
  if (axis.lengthSq() < 1e-12) return new THREE.Quaternion();
  return new THREE.Quaternion().setFromAxisAngle(axis, joint.defaultValue);
}

export function jointMotionOffset(joint: { type: string; axis: Vec3; defaultValue: number }): THREE.Vector3 {
  if (joint.type !== "prismatic") return new THREE.Vector3();
  const axis = v3(joint.axis).normalize();
  return axis.multiplyScalar(joint.defaultValue);
}

export function computeLinkWorldTransforms(model: RobotModel): Map<string, Transform> {
  const linkById = new Map(model.links.map((l) => [l.id, l]));
  const childIds = new Set(model.joints.map((j) => j.childLinkId));
  const roots = model.links.filter((l) => !childIds.has(l.id));
  const out = new Map<string, Transform>();

  function visitLink(linkId: string, parentTf: Transform) {
    const link = linkById.get(linkId);
    if (!link) return;
    const linkTf = compose(parentTf, link.frame.position, link.frame.rotation);
    out.set(linkId, linkTf);

    for (const joint of model.joints.filter((j) => j.parentLinkId === linkId)) {
      const jOffset = v3(joint.originPosition).add(jointMotionOffset(joint));
      const jRot = q4(joint.originRotation).multiply(jointMotionQuat(joint));
      const jointTf = compose(linkTf, { x: jOffset.x, y: jOffset.y, z: jOffset.z }, {
        x: jRot.x,
        y: jRot.y,
        z: jRot.z,
        w: jRot.w,
      });
      visitLink(joint.childLinkId, jointTf);
    }
  }

  for (const root of roots) {
    const rootTf = compose(
      { position: new THREE.Vector3(), quaternion: new THREE.Quaternion() },
      root.frame.position,
      root.frame.rotation
    );
    out.set(root.id, rootTf);
    for (const joint of model.joints.filter((j) => j.parentLinkId === root.id)) {
      const jOffset = v3(joint.originPosition).add(jointMotionOffset(joint));
      const jRot = q4(joint.originRotation).multiply(jointMotionQuat(joint));
      const jointTf = compose(rootTf, { x: jOffset.x, y: jOffset.y, z: jOffset.z }, {
        x: jRot.x,
        y: jRot.y,
        z: jRot.z,
        w: jRot.w,
      });
      visitLink(joint.childLinkId, jointTf);
    }
  }

  return out;
}

export function computeJointWorldTransforms(model: RobotModel): Map<string, Transform> {
  const linkTfs = computeLinkWorldTransforms(model);
  const out = new Map<string, Transform>();

  for (const joint of model.joints) {
    const parentTf = linkTfs.get(joint.parentLinkId);
    if (!parentTf) continue;
    const jOffset = v3(joint.originPosition).add(jointMotionOffset(joint));
    const jRot = q4(joint.originRotation).multiply(jointMotionQuat(joint));
    out.set(joint.id, compose(parentTf, { x: jOffset.x, y: jOffset.y, z: jOffset.z }, {
      x: jRot.x,
      y: jRot.y,
      z: jRot.z,
      w: jRot.w,
    }));
  }

  return out;
}

export function computeShapeWorldTransform(
  model: RobotModel,
  linkId: string,
  shape: PrimitiveShape
): Transform | null {
  const linkTf = computeLinkWorldTransforms(model).get(linkId);
  if (!linkTf) return null;
  const visualRot = shapeVisualQuaternion(shape);
  const position = v3(shape.localPosition).applyQuaternion(linkTf.quaternion).add(linkTf.position);
  return {
    position,
    quaternion: linkTf.quaternion.clone().multiply(visualRot),
  };
}

/** Parent link frame for a child link (incoming joint origin frame). */
export function parentFrameForLink(model: RobotModel, linkId: string): Transform | null {
  const joint = model.joints.find((j) => j.childLinkId === linkId);
  if (!joint) return null;
  return computeJointWorldTransforms(model).get(joint.id) ?? null;
}

export function toVec3(v: THREE.Vector3): Vec3 {
  return { x: v.x, y: v.y, z: v.z };
}

export function toQuat(q: THREE.Quaternion): Quat {
  return { x: q.x, y: q.y, z: q.z, w: q.w };
}

export function invertTransform(tf: Transform): Transform {
  const inv = tf.quaternion.clone().invert();
  return {
    position: tf.position.clone().negate().applyQuaternion(inv),
    quaternion: inv,
  };
}

export function relativeTransform(parent: Transform, world: Transform): Transform {
  const inv = invertTransform(parent);
  return {
    position: world.position.clone().sub(parent.position).applyQuaternion(inv.quaternion),
    quaternion: inv.quaternion.clone().multiply(world.quaternion),
  };
}

function shapeLocalBoundingBox(shape: PrimitiveShape): THREE.Box3 {
  const d = shape.dimensions;
  let geom: THREE.BufferGeometry;
  switch (shape.type) {
    case "box":
      geom = new THREE.BoxGeometry(d[0], d[1], d[2]);
      break;
    case "cylinder":
      geom = new THREE.CylinderGeometry(d[0], d[0], d[1] ?? d[0], 16);
      break;
    case "sphere":
      geom = new THREE.SphereGeometry(d[0], 16, 16);
      break;
    case "capsule":
      geom = new THREE.CapsuleGeometry(d[0], Math.max(0.01, (d[1] ?? 0.1) - 2 * d[0]), 8, 16);
      break;
    default:
      geom = new THREE.BoxGeometry(0.1, 0.1, 0.1);
  }
  geom.computeBoundingBox();
  const box = geom.boundingBox!.clone();
  geom.dispose();
  return box;
}

const _worldCorner = new THREE.Vector3();

function forEachBoundingBoxCorner(box: THREE.Box3, fn: (corner: THREE.Vector3) => void) {
  const { min, max } = box;
  for (const x of [min.x, max.x]) {
    for (const y of [min.y, max.y]) {
      for (const z of [min.z, max.z]) {
        fn(new THREE.Vector3(x, y, z));
      }
    }
  }
}

/** Z translation so the lowest shape geometry sits on z=0 (visual-only). */
export function computeVisualGroundOffset(model: RobotModel): number {
  const linkTfs = computeLinkWorldTransforms(model);
  let minZ = Infinity;

  for (const link of model.links) {
    const linkTf = linkTfs.get(link.id);
    if (!linkTf) continue;

    for (const shape of link.shapes) {
      const visualRot = shapeVisualQuaternion(shape);
      const position = v3(shape.localPosition).applyQuaternion(linkTf.quaternion).add(linkTf.position);
      const quaternion = linkTf.quaternion.clone().multiply(visualRot);
      const localBox = shapeLocalBoundingBox(shape);

      forEachBoundingBoxCorner(localBox, (corner) => {
        _worldCorner.copy(corner).applyQuaternion(quaternion).add(position);
        minZ = Math.min(minZ, _worldCorner.z);
      });
    }
  }

  return Number.isFinite(minZ) ? -minZ : 0;
}
