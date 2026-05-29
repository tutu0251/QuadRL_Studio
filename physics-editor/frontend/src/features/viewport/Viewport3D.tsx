import { Canvas } from "@react-three/fiber";
import { Grid, OrbitControls } from "@react-three/drei";
import { PhysicsScene } from "./PhysicsScene";
import { ViewportOverlay } from "./ViewportOverlay";
import { useEditorStore } from "../../stores/editorStore";

export function Viewport3D() {
  const setSelection = useEditorStore((s) => s.setSelection);

  return (
    <div className="viewport-wrap">
      <Canvas
        className="viewport"
        camera={{ position: [1.2, 0.9, 1.2], fov: 50 }}
        onPointerMissed={() => setSelection(null)}
      >
        <color attach="background" args={["#151820"]} />
        <fog attach="fog" args={["#151820", 4, 18]} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[4, 6, 3]} intensity={1.0} castShadow />
        <directionalLight position={[-2, 2, -2]} intensity={0.25} />
        <Grid infiniteGrid cellSize={0.1} sectionSize={1} fadeDistance={25} sectionColor="#3a4556" cellColor="#2a3340" />
        <PhysicsScene />
        <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
      </Canvas>
      <ViewportOverlay />
    </div>
  );
}
