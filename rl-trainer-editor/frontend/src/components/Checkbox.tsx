export function Checkbox({
  checked,
  onChange,
  label,
  hint,
  disabled,
  id,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
  hint?: string;
  disabled?: boolean;
  id?: string;
}) {
  const input = (
    <input
      id={id}
      type="checkbox"
      className="param-checkbox"
      checked={checked}
      disabled={disabled}
      title={hint}
      onChange={(e) => onChange(e.target.checked)}
    />
  );

  if (!label) {
    return <span className={`checkbox-row checkbox-row-bare ${disabled ? "disabled" : ""}`}>{input}</span>;
  }

  return (
    <label className={`checkbox-row ${disabled ? "disabled" : ""}`} title={hint}>
      {input}
      <span className="checkbox-label">{label}</span>
    </label>
  );
}
