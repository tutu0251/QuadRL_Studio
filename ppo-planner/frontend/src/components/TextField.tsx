export function TextField({
  label,
  value,
  onChange,
  hint,
  disabled,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
  disabled?: boolean;
  placeholder?: string;
}) {
  return (
    <div className="param-field">
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
        type="text"
        className="param-input"
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
