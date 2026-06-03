import { useMemo, type ReactNode } from "react";
import { useEditorStore } from "../../stores/editorStore";
import { computeVisualGroundOffset } from "../../utils/kinematics";

/** Lifts the robot so its lowest geometry rests on the z=0 ground plane. */
export function GroundedRobot({ children }: { children: ReactNode }) {
  const model = useEditorStore((s) => s.model);
  const groundZ = useMemo(() => (model ? computeVisualGroundOffset(model) : 0), [model]);

  return <group position={[0, 0, groundZ]}>{children}</group>;
}
