import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid, GizmoHelper, GizmoViewport } from "@react-three/drei";
import { RobotScene } from "./RobotScene";
import { GizmoLayer } from "./GizmoLayer";
import { MeasurementOverlay } from "./MeasurementOverlay";
import { GroundedRobot } from "./GroundedRobot";

/** URDF/SDF/Gazebo use Z-up; match that in the scene view. */
const WORLD_UP: [number, number, number] = [0, 0, 1];

export function Viewport3D() {
  return (
    <div className="viewport">
      <Canvas
        camera={{ position: [1.2, 1.2, 1.0], fov: 50, near: 0.01, far: 100, up: WORLD_UP }}
      >
        <color attach="background" args={["#1a1d24"]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[2, 2, 4]} intensity={0.8} />
        <Grid
          args={[2, 20]}
          rotation={[Math.PI / 2, 0, 0]}
          cellColor="#333333"
          sectionColor="#444444"
        />
        <axesHelper args={[0.3]} />
        <GroundedRobot>
          <RobotScene />
          <GizmoLayer />
          <MeasurementOverlay />
        </GroundedRobot>
        <OrbitControls makeDefault enableDamping up={WORLD_UP} />
        <GizmoHelper alignment="bottom-right" margin={[60, 60]}>
          <GizmoViewport />
        </GizmoHelper>
      </Canvas>
    </div>
  );
}
