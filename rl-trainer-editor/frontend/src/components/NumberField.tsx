export function NumberField({
  label,
  value,
  onChange,
  step = 0.01,
  min,
  hint,
  disabled,
  status,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  hint?: string;
  disabled?: boolean;
  status?: "ok" | "warn";
}) {
  return (
    <div className={`param-field ${status ? `param-${status}` : ""}`}>
      <span className="param-label-row">
        <span className="param-label" title={hint}>
          {label}
        </span>
        {hint ? (
          <span className="param-hint-icon" title={hint} aria-label={hint}>
            ⓘ
          </span>
        ) : null}
      </span>
      <input
        type="number"
        className="param-input"
        step={step}
        min={min}
        disabled={disabled}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}
