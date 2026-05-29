import * as THREE from "three";
import type { Quat, RobotModel, Vec3 } from "@robot-model";

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

export function computeLinkWorldTransforms(model: RobotModel): Map<string, Transform> {
  const childIds = new Set(model.joints.map((j) => j.childLinkId));
  const roots = model.links.filter((l) => !childIds.has(l.id));
  const out = new Map<string, Transform>();
  const identity: Transform = {
    position: new THREE.Vector3(),
    quaternion: new THREE.Quaternion(),
  };

  function visit(linkId: string, parentTf: Transform) {
    const link = model.links.find((l) => l.id === linkId);
    if (!link) return;
    const linkTf = compose(parentTf, link.frame.position, link.frame.rotation);
    out.set(linkId, linkTf);
    for (const joint of model.joints.filter((j) => j.parentLinkId === linkId)) {
      const jointTf = compose(linkTf, joint.originPosition, joint.originRotation);
      visit(joint.childLinkId, jointTf);
    }
  }

  for (const root of roots) {
    visit(root.id, identity);
  }
  return out;
}
