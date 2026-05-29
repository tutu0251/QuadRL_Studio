import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid, GizmoHelper, GizmoViewport } from "@react-three/drei";
import { RobotScene } from "./RobotScene";
import { GizmoLayer } from "./GizmoLayer";
import { MeasurementOverlay } from "./MeasurementOverlay";

export function Viewport3D() {
  return (
    <div className="viewport">
      <Canvas camera={{ position: [1.2, 1.0, 1.2], fov: 50, near: 0.01, far: 100 }}>
        <color attach="background" args={["#1a1d24"]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[2, 3, 2]} intensity={0.8} />
        <Grid args={[2, 20]} cellColor="#333333" sectionColor="#444444" />
        <axesHelper args={[0.3]} />
        <RobotScene />
        <GizmoLayer />
        <MeasurementOverlay />
        <OrbitControls makeDefault enableDamping />
        <GizmoHelper alignment="bottom-right" margin={[60, 60]}>
          <GizmoViewport />
        </GizmoHelper>
      </Canvas>
    </div>
  );
}
