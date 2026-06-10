import type { FieldMeta } from "../labels";
import { FieldLabel } from "./FieldLabel";

/** On/off switch with a friendly label + code sublabel. */
export function Toggle({
  meta,
  checked,
  onChange,
  disabled,
}: {
  meta: FieldMeta;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={`tp-toggle-row ${disabled ? "tp-disabled" : ""}`}>
      <FieldLabel meta={meta} />
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={meta.label}
        disabled={disabled}
        className={`tp-switch ${checked ? "on" : ""}`}
        onClick={() => !disabled && onChange(!checked)}
      >
        <span className="tp-switch-thumb" />
      </button>
    </label>
  );
}
