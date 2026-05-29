import type { Quat, Vec3 } from "@robot-model";
import { Vector3Field } from "./Vector3Field";
import { eulerDegToQuat, quatToEulerDeg } from "../utils/euler";

interface Props {
  position: Vec3;
  rotation: Quat;
  onPositionChange: (position: Vec3) => void | Promise<void>;
  onRotationChange: (rotation: Quat) => void | Promise<void>;
  /** When set, shows Scale row (e.g. shape dimensions). */
  scale?: Vec3;
  onScaleChange?: (scale: Vec3) => void | Promise<void>;
  scaleLabels?: [string, string, string];
  positionStep?: number;
  rotationStep?: number;
  scaleStep?: number;
}

export function TransformSection({
  position,
  rotation,
  onPositionChange,
  onRotationChange,
  scale,
  onScaleChange,
  scaleLabels = ["X", "Y", "Z"],
  positionStep = 0.01,
  rotationStep = 1,
  scaleStep = 0.01,
}: Props) {
  const euler = quatToEulerDeg(rotation);

  const updatePos = (axis: "x" | "y" | "z", val: number) => {
    void onPositionChange({ ...position, [axis]: val });
  };

  const updateRot = (axis: "x" | "y" | "z", val: number) => {
    void onRotationChange(eulerDegToQuat({ ...euler, [axis]: val }));
  };

  const updateScale = (axis: "x" | "y" | "z", val: number) => {
    if (scale && onScaleChange) {
      void onScaleChange({ ...scale, [axis]: val });
    }
  };

  return (
    <div className="transform-section">
      <Vector3Field
        label="Position"
        x={position.x}
        y={position.y}
        z={position.z}
        onChange={updatePos}
        step={positionStep}
      />
      <Vector3Field
        label="Rotation"
        x={euler.x}
        y={euler.y}
        z={euler.z}
        onChange={updateRot}
        step={rotationStep}
      />
      {scale && onScaleChange && (
        <Vector3Field
          label="Scale"
          x={scale.x}
          y={scale.y}
          z={scale.z}
          onChange={updateScale}
          step={scaleStep}
          axisLabels={scaleLabels}
        />
      )}
    </div>
  );
}
