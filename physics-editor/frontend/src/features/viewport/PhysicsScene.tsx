import { useMemo } from "react";
import * as THREE from "three";
import { Cone, Line } from "@react-three/drei";
import type { ThreeEvent } from "@react-three/fiber";
import type { Link, PrimitiveShape, RobotModel } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";
import { principalInertia } from "../../utils/inertia";
import { shapeVisualQuaternion } from "../../utils/primitiveVisual";

function hexColor(c: string): number {
  const h = c.startsWith("#") ? c.slice(1) : c;
  return parseInt(h.padEnd(6, "0").slice(0, 6), 16);
}

function PrimitiveMesh({ shape, dimmed }: { shape: PrimitiveShape; dimmed: boolean }) {
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
        metalness={0.1}
        roughness={0.85}
        transparent
        opacity={dimmed ? 0.45 : 0.65}
      />
    </mesh>
  );
}

function InertiaArrow({
  origin,
  direction,
  length,
  color,
}: {
  origin: THREE.Vector3;
  direction: THREE.Vector3;
  length: number;
  color: string;
}) {
  const dir = direction.clone().normalize();
  const tip = origin.clone().add(dir.clone().multiplyScalar(length));
  const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  return (
    <group>
      <Line points={[origin, tip]} color={color} lineWidth={2.5} />
      <Cone args={[length * 0.06, length * 0.14, 8]} position={tip} quaternion={quat}>
        <meshBasicMaterial color={color} />
      </Cone>
    </group>
  );
}

/** COM + principal inertia axes in link-local frame (same parent group as visual meshes). */
function LinkPhysicsOverlay({ link }: { link: Link }) {
  const showCom = useEditorStore((s) => s.showCom);
  const showAxes = useEditorStore((s) => s.showInertiaAxes);
  const selected = useEditorStore((s) => s.selection);
  const isSel = selected?.kind === "link" && selected.id === link.id;

  const ins = link.inertial;
  const origin = useMemo(
    () => new THREE.Vector3(ins.com.x, ins.com.y, ins.com.z),
    [ins.com.x, ins.com.y, ins.com.z]
  );
  const inertialRot = useMemo(
    () => new THREE.Quaternion(ins.comRotation.x, ins.comRotation.y, ins.comRotation.z, ins.comRotation.w),
    [ins.comRotation]
  );

  const { axes, values } = useMemo(
    () => principalInertia(ins.ixx, ins.ixy, ins.ixz, ins.iyy, ins.iyz, ins.izz),
    [ins.ixx, ins.ixy, ins.ixz, ins.iyy, ins.iyz, ins.izz]
  );

  const maxVal = Math.max(...values, 1e-6);
  const scale = 0.08 * (isSel ? 1.2 : 0.9);
  const localAxes = useMemo(
    () => axes.map((a) => a.clone().applyQuaternion(inertialRot).normalize()),
    [axes, inertialRot]
  );
  const colors = ["#ff4444", "#44ff44", "#4488ff"];

  return (
    <group>
      {showCom && (
        <mesh position={origin}>
          <sphereGeometry args={[0.012, 12, 12]} />
          <meshBasicMaterial color={isSel ? "#ffcc00" : "#ff8800"} />
        </mesh>
      )}
      {showAxes &&
        localAxes.map((axis, i) => (
          <InertiaArrow
            key={i}
            origin={origin}
            direction={axis}
            length={scale * (0.5 + values[i] / maxVal)}
            color={colors[i]}
          />
        ))}
    </group>
  );
}

function LinkGroup({ link, model }: { link: Link; model: RobotModel }) {
  const setSelection = useEditorStore((s) => s.setSelection);
  const linkMap = useMemo(() => new Map(model.links.map((l) => [l.id, l])), [model.links]);

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    setSelection({ kind: "link", id: link.id });
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
      onClick={handleClick}
    >
      {link.shapes.map((s) => (
        <PrimitiveMesh key={s.id} shape={s} dimmed />
      ))}
      <LinkPhysicsOverlay link={link} />
      {model.joints
        .filter((j) => j.parentLinkId === link.id)
        .map((j) => {
          const child = linkMap.get(j.childLinkId);
          if (!child) return null;
          return (
            <group
              key={j.id}
              position={[j.originPosition.x, j.originPosition.y, j.originPosition.z]}
              quaternion={new THREE.Quaternion(
                j.originRotation.x,
                j.originRotation.y,
                j.originRotation.z,
                j.originRotation.w
              )}
            >
              <LinkGroup link={child} model={model} />
            </group>
          );
        })}
    </group>
  );
}

function WholeRobotComMarker() {
  const com = useEditorStore((s) => s.wholeCom);
  const show = useEditorStore((s) => s.showWholeCom);
  if (!show || !com) return null;
  return (
    <mesh position={[com.x, com.y, com.z]}>
      <sphereGeometry args={[0.02, 16, 16]} />
      <meshBasicMaterial color="#00ffff" wireframe />
    </mesh>
  );
}

export function PhysicsScene() {
  const model = useEditorStore((s) => s.model);
  if (!model) return null;
  const childIds = new Set(model.joints.map((j) => j.childLinkId));
  const roots = model.links.filter((l) => !childIds.has(l.id));

  return (
    <group>
      {roots.map((r) => (
        <LinkGroup key={r.id} link={r} model={model} />
      ))}
      <WholeRobotComMarker />
    </group>
  );
}
