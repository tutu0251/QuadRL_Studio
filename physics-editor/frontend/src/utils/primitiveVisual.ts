import * as THREE from "three";
import type { PrimitiveShape } from "@robot-model";

export function shapeVisualQuaternion(shape: PrimitiveShape): THREE.Quaternion {
  const q = new THREE.Quaternion(
    shape.localRotation.x,
    shape.localRotation.y,
    shape.localRotation.z,
    shape.localRotation.w
  );
  if (shape.type === "cylinder" || shape.type === "capsule") {
    q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2));
  }
  return q;
}
