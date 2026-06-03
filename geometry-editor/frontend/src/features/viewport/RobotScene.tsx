import { useMemo } from "react";
import * as THREE from "three";
import { Line } from "@react-three/drei";
import type { ThreeEvent } from "@react-three/fiber";
import type { Joint, Link, PrimitiveShape, RobotModel } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";
import { jointMotionOffset, jointMotionQuat } from "../../utils/kinematics";
import { shapeVisualQuaternion } from "../../utils/primitiveVisual";

function hexColor(c: string): number {
  const h = c.startsWith("#") ? c.slice(1) : c;
  return parseInt(h.padEnd(6, "0").slice(0, 6), 16);
}

function FrameAxes({ size = 0.06 }: { size?: number }) {
  return (
    <group>
      <Line points={[[0, 0, 0], [size, 0, 0]]} color="#ff0000" lineWidth={2} />
      <Line points={[[0, 0, 0], [0, size, 0]]} color="#00ff00" lineWidth={2} />
      <Line points={[[0, 0, 0], [0, 0, size]]} color="#0000ff" lineWidth={2} />
    </group>
  );
}

function JointAxisArrow({ axis, length = 0.12 }: { axis: { x: number; y: number; z: number }; length?: number }) {
  const dir = new THREE.Vector3(axis.x, axis.y, axis.z).normalize();
  return (
    <Line
      points={[[0, 0, 0], [dir.x * length, dir.y * length, dir.z * length]]}
      color="#ffff00"
      lineWidth={3}
    />
  );
}

function PrimitiveMesh({ shape, selected }: { shape: PrimitiveShape; selected: boolean }) {
  const d = shape.dimensions;
  const geom = useMemo(() => {
    switch (shape.type) {
      case "box":
        return new THREE.BoxGeometry(d[0], d[1], d[2]);
      case "cylinder":
        return new THREE.CylinderGeometry(d[0], d[0], d[1] ?? d[0], 16);
      case "sphere":
        return new THREE.SphereGeometry(d[0], 16, 16);
      case "capsule":
        return new THREE.CapsuleGeometry(d[0], Math.max(0.01, (d[1] ?? 0.1) - 2 * d[0]), 8, 16);
      default:
        return new THREE.BoxGeometry(0.1, 0.1, 0.1);
    }
  }, [shape.type, d]);

  return (
    <mesh
      geometry={geom}
      position={[shape.localPosition.x, shape.localPosition.y, shape.localPosition.z]}
      quaternion={shapeVisualQuaternion(shape)}
    >
      <meshStandardMaterial
        color={hexColor(shape.color)}
        metalness={0.2}
        roughness={0.7}
        emissive={selected ? new THREE.Color(0x224466) : new THREE.Color(0x000000)}
      />
    </mesh>
  );
}

function LinkGroup({
  link,
  model,
  onSelectLink,
  onSelectJoint,
  onSelectShape,
}: {
  link: Link;
  model: RobotModel;
  onSelectLink: (id: string) => void;
  onSelectJoint: (id: string) => void;
  onSelectShape: (linkId: string, shapeId: string) => void;
}) {
  const selection = useEditorStore((s) => s.selection);
  const showLinkFrames = useEditorStore((s) => s.showLinkFrames);
  const showJointFrames = useEditorStore((s) => s.showJointFrames);
  const showJointAxes = useEditorStore((s) => s.showJointAxes);
  const linkMap = useMemo(() => new Map(model.links.map((l) => [l.id, l])), [model.links]);

  const selLink = selection?.kind === "link" && selection.id === link.id;

  const handleClick = (e: ThreeEvent<MouseEvent>, fn: () => void) => {
    e.stopPropagation();
    fn();
  };

  return (
    <group
      position={[link.frame.position.x, link.frame.position.y, link.frame.position.z]}
      quaternion={new THREE.Quaternion(
        link.frame.rotation.x,
        link.frame.rotation.y,
        link.frame.rotation.z,
        link.frame.rotation.w
      )}
      onClick={(e) => handleClick(e, () => onSelectLink(link.id))}
    >
      {link.shapes.map((s) => {
        const sel =
          selection?.kind === "shape" && selection.linkId === link.id && selection.shapeId === s.id;
        return (
          <group key={s.id} onClick={(e) => handleClick(e, () => onSelectShape(link.id, s.id))}>
            <PrimitiveMesh shape={s} selected={!!sel} />
          </group>
        );
      })}
      {showLinkFrames && <FrameAxes size={selLink ? 0.08 : 0.06} />}

      {model.joints
        .filter((j) => j.parentLinkId === link.id)
        .map((j) => (
          <JointGroup
            key={j.id}
            joint={j}
            childLink={linkMap.get(j.childLinkId)}
            model={model}
            showJointFrames={showJointFrames}
            showJointAxes={showJointAxes}
            onSelectJoint={onSelectJoint}
            onSelectLink={onSelectLink}
            onSelectShape={onSelectShape}
          />
        ))}
    </group>
  );
}

function JointGroup({
  joint,
  childLink,
  model,
  showJointFrames,
  showJointAxes,
  onSelectJoint,
  onSelectLink,
  onSelectShape,
}: {
  joint: Joint;
  childLink?: Link;
  model: RobotModel;
  showJointFrames: boolean;
  showJointAxes: boolean;
  onSelectJoint: (id: string) => void;
  onSelectLink: (id: string) => void;
  onSelectShape: (linkId: string, shapeId: string) => void;
}) {
  const selection = useEditorStore((s) => s.selection);
  const selJoint = selection?.kind === "joint" && selection.id === joint.id;

  const handleClick = (e: ThreeEvent<MouseEvent>, fn: () => void) => {
    e.stopPropagation();
    fn();
  };

  if (!childLink) return null;

  const motionOffset = jointMotionOffset(joint);
  const originRot = new THREE.Quaternion(
    joint.originRotation.x,
    joint.originRotation.y,
    joint.originRotation.z,
    joint.originRotation.w
  ).multiply(jointMotionQuat(joint));

  return (
    <group
      position={[
        joint.originPosition.x + motionOffset.x,
        joint.originPosition.y + motionOffset.y,
        joint.originPosition.z + motionOffset.z,
      ]}
      quaternion={originRot}
      onClick={(e) => handleClick(e, () => onSelectJoint(joint.id))}
    >
      {showJointFrames && <FrameAxes size={selJoint ? 0.07 : 0.05} />}
      {showJointAxes && joint.type !== "fixed" && <JointAxisArrow axis={joint.axis} />}
      <LinkGroup
        link={childLink}
        model={model}
        onSelectLink={onSelectLink}
        onSelectJoint={onSelectJoint}
        onSelectShape={onSelectShape}
      />
    </group>
  );
}

export function RobotScene() {
  const model = useEditorStore((s) => s.model);
  const setSelection = useEditorStore((s) => s.setSelection);

  if (!model) return null;

  const childIds = new Set(model.joints.map((j) => j.childLinkId));
  const roots = model.links.filter((l) => !childIds.has(l.id));

  return (
    <group>
      {roots.map((r) => (
        <LinkGroup
          key={r.id}
          link={r}
          model={model}
          onSelectLink={(id) => setSelection({ kind: "link", id })}
          onSelectJoint={(id) => setSelection({ kind: "joint", id })}
          onSelectShape={(linkId, shapeId) => setSelection({ kind: "shape", linkId, shapeId })}
        />
      ))}
    </group>
  );
}
