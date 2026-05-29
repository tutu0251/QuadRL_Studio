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
      <span className="field-label" title={hint}>
        {label}
      </span>
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
