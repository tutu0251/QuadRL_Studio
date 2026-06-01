import { FieldLabel } from "./FieldLabel";

export function NumberField({
  label,
  value,
  onChange,
  step = 0.01,
  min,
  hint,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  hint?: string;
  disabled?: boolean;
}) {
  return (
    <div className="inspector-row">
      <FieldLabel label={label} hint={hint} />
      <input
        type="number"
        step={step}
        min={min}
        disabled={disabled}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}
