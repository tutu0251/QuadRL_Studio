/** Three.js primitive axis conventions differ from URDF/SDF (Z-up length). */
import * as THREE from "three";
import type { PrimitiveShape, Quat } from "@robot-model";

/** Three.js cylinder/capsule geometries are Y-aligned; robot primitives are Z-aligned (URDF/SDF). */
export const Z_ALIGNED_VISUAL_ROTATION = new THREE.Quaternion().setFromAxisAngle(
  new THREE.Vector3(1, 0, 0),
  Math.PI / 2
);

/** @deprecated Use Z_ALIGNED_VISUAL_ROTATION */
export const CAPSULE_VISUAL_ROTATION = Z_ALIGNED_VISUAL_ROTATION;

function usesZAlignedVisual(type: PrimitiveShape["type"]): boolean {
  return type === "cylinder" || type === "capsule";
}

export function shapeVisualQuaternion(shape: PrimitiveShape): THREE.Quaternion {
  const q = new THREE.Quaternion(
    shape.localRotation.x,
    shape.localRotation.y,
    shape.localRotation.z,
    shape.localRotation.w
  );
  if (usesZAlignedVisual(shape.type)) {
    q.multiply(Z_ALIGNED_VISUAL_ROTATION);
  }
  return q;
}

export function shapeLocalRotationFromVisual(visualQuat: THREE.Quaternion, shapeType: PrimitiveShape["type"]): Quat {
  const q = visualQuat.clone();
  if (usesZAlignedVisual(shapeType)) {
    q.multiply(Z_ALIGNED_VISUAL_ROTATION.clone().invert());
  }
  return { x: q.x, y: q.y, z: q.z, w: q.w };
}
