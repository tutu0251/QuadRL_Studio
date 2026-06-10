import type { FieldMeta } from "../labels";
import { FieldLabel } from "./FieldLabel";

/** Dropdown with a friendly label + code sublabel. Values are strings; map them outside. */
export function SelectField({
  meta,
  value,
  options,
  onChange,
  disabled,
}: {
  meta: FieldMeta;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="tp-field">
      <FieldLabel meta={meta} />
      <select
        className="tp-input tp-select-input"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
