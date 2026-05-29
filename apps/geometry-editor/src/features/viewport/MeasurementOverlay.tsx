import { Line, Html } from "@react-three/drei";
import { useEditorStore } from "../../stores/editorStore";

export function MeasurementOverlay() {
  const measurement = useEditorStore((s) => s.measurement);
  if (!measurement || measurement.points.length < 2) return null;

  const [a, b] = measurement.points;
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, z: (a.z + b.z) / 2 };

  return (
    <group>
      <Line
        points={[
          [a.x, a.y, a.z],
          [b.x, b.y, b.z],
        ]}
        color="#ffcc00"
        lineWidth={2}
      />
      <Html position={[mid.x, mid.y + 0.05, mid.z]} center>
        <div className="measure-label">
          {measurement.value.toFixed(3)} {measurement.unit}
        </div>
      </Html>
    </group>
  );
}
