import { FieldLabel } from "./FieldLabel";
import { NumberField } from "./NumberField";

interface Props {
  label: string;
  x: number;
  y: number;
  z: number;
  onChange: (axis: "x" | "y" | "z", value: number) => void;
  step?: number;
  axisLabels?: [string, string, string];
  hint?: string;
}

export function Vector3Field({ label, x, y, z, onChange, step = 0.01, axisLabels = ["X", "Y", "Z"], hint }: Props) {
  const colors = ["axis-x", "axis-y", "axis-z"];
  return (
    <div className="vector3-field">
      <FieldLabel label={label} hint={hint} />
      <div className="vector3-inputs">
        {(["x", "y", "z"] as const).map((axis, i) => (
          <label key={axis} className={colors[i]}>
            {axisLabels[i]}
            <NumberField
              step={step}
              value={Number.isFinite(axis === "x" ? x : axis === "y" ? y : z) ? (axis === "x" ? x : axis === "y" ? y : z) : 0}
              onCommit={(v) => onChange(axis, v)}
            />
          </label>
        ))}
      </div>
    </div>
  );
}
