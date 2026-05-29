import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { TransformControls } from "@react-three/drei";
import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";
import {
  computeJointWorldTransforms,
  computeLinkWorldTransforms,
  computeShapeWorldTransform,
  parentFrameForLink,
  relativeTransform,
  toQuat,
  toVec3,
} from "../../utils/kinematics";
import { shapeLocalRotationFromVisual } from "../../utils/primitiveVisual";

type GizmoTargetData =
  | { type: "link"; id: string }
  | { type: "joint"; id: string }
  | { type: "shape"; linkId: string; shapeId: string; dimensions: number[] };

export function GizmoLayer() {
  const model = useEditorStore((s) => s.model);
  const project = useEditorStore((s) => s.project);
  const selection = useEditorStore((s) => s.selection);
  const gizmoMode = useEditorStore((s) => s.gizmoMode);
  const gizmoTarget = useEditorStore((s) => s.gizmoTarget);
  const setModel = useEditorStore((s) => s.setModel);
  const [obj] = useState(() => new THREE.Group());
  const dragging = useRef(false);
  const worldTfRef = useRef<THREE.Matrix4>(new THREE.Matrix4());

  const target: GizmoTargetData | null = useMemo(() => {
    if (!model || !selection) return null;
    if (gizmoTarget === "link" && selection.kind === "link") {
      return { type: "link", id: selection.id };
    }
    if (gizmoTarget === "joint" && selection.kind === "joint") {
      return { type: "joint", id: selection.id };
    }
    if (gizmoTarget === "shape" && selection.kind === "shape") {
      const link = model.links.find((l) => l.id === selection.linkId);
      const shape = link?.shapes.find((s) => s.id === selection.shapeId);
      if (!shape) return null;
      return {
        type: "shape",
        linkId: selection.linkId,
        shapeId: selection.shapeId,
        dimensions: [...shape.dimensions],
      };
    }
    return null;
  }, [model, selection, gizmoTarget]);

  useEffect(() => {
    if (!model || !target) return;

    let worldTf: { position: THREE.Vector3; quaternion: THREE.Quaternion } | null = null;

    if (target.type === "link") {
      worldTf = computeLinkWorldTransforms(model).get(target.id) ?? null;
    } else if (target.type === "joint") {
      worldTf = computeJointWorldTransforms(model).get(target.id) ?? null;
    } else {
      const link = model.links.find((l) => l.id === target.linkId);
      const shape = link?.shapes.find((s) => s.id === target.shapeId);
      worldTf = link && shape ? computeShapeWorldTransform(model, link.id, shape) : null;
    }

    if (!worldTf) return;

    obj.position.copy(worldTf.position);
    obj.quaternion.copy(worldTf.quaternion);
    obj.scale.set(1, 1, 1);
    obj.updateMatrixWorld(true);
    worldTfRef.current.copy(obj.matrixWorld);
  }, [model, target, obj]);

  const commit = async () => {
    if (!project || !target || !model) return;

    const newWorld = {
      position: obj.position.clone(),
      quaternion: obj.quaternion.clone(),
    };

    if (target.type === "link") {
      const parent = parentFrameForLink(model, target.id);
      const local = parent
        ? relativeTransform(parent, newWorld)
        : newWorld;
      await api.updateLinkFrame(project, target.id, {
        position: toVec3(local.position),
        rotation: toQuat(local.quaternion),
      });
    } else if (target.type === "joint") {
      const joint = model.joints.find((j) => j.id === target.id);
      if (!joint) return;
      const parentLinkTf = computeLinkWorldTransforms(model).get(joint.parentLinkId);
      if (!parentLinkTf) return;
      const local = relativeTransform(parentLinkTf, newWorld);
      await api.updateJoint(project, target.id, {
        originPosition: toVec3(local.position),
        originRotation: toQuat(local.quaternion),
      });
    } else if (target.type === "shape") {
      const link = model.links.find((l) => l.id === target.linkId);
      const shape = link?.shapes.find((s) => s.id === target.shapeId);
      if (!link || !shape) return;
      const linkTf = computeLinkWorldTransforms(model).get(link.id);
      if (!linkTf) return;

      if (gizmoMode === "scale") {
        const dims = target.dimensions.map((d, i) =>
          Math.max(0.01, d * (i === 0 ? obj.scale.x : i === 1 ? obj.scale.y : obj.scale.z))
        );
        await api.updateDimensions(project, target.linkId, target.shapeId, dims);
        obj.scale.set(1, 1, 1);
      } else {
        const local = relativeTransform(linkTf, newWorld);
        await api.updateTransform(
          project,
          target.linkId,
          target.shapeId,
          toVec3(local.position),
          shapeLocalRotationFromVisual(local.quaternion, shape.type)
        );
      }
    }
    setModel(await api.getModel(project));
  };

  if (!target) return null;

  return (
    <>
      <primitive object={obj} />
      <TransformControls
        object={obj}
        mode={gizmoMode}
        onMouseDown={() => {
          dragging.current = true;
        }}
        onMouseUp={() => {
          if (dragging.current) {
            dragging.current = false;
            void commit();
          }
        }}
      />
    </>
  );
}
