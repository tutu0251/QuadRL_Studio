import type { Vec3 } from "@robot-model";

export function Vector3Field({
  label,
  value,
  onChange,
  step = 0.001,
}: {
  label: string;
  value: Vec3;
  onChange: (v: Vec3) => void;
  step?: number;
}) {
  const axes: { key: keyof Vec3; cls: string }[] = [
    { key: "x", cls: "axis-x" },
    { key: "y", cls: "axis-y" },
    { key: "z", cls: "axis-z" },
  ];
  return (
    <div className="vector3-field">
      <span className="field-label">{label}</span>
      <div className="vector3-inputs">
        {axes.map(({ key, cls }) => (
          <label key={key} className={cls}>
            {key.toUpperCase()}
            <input
              type="number"
              step={step}
              value={value[key]}
              onChange={(e) => onChange({ ...value, [key]: parseFloat(e.target.value) || 0 })}
            />
          </label>
        ))}
      </div>
    </div>
  );
}
