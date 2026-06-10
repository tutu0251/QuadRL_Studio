import { useEffect, useRef, useState } from "react";
import type { FieldMeta } from "../labels";
import { FieldLabel } from "./FieldLabel";

/**
 * Numeric input with a friendly label. Edits stay local until blur/Enter (so partial
 * typing never fights the controlled value). When `nullable`, an empty box commits `null`
 * — used for "leave blank for all / no limit" fields like Curriculum Stages.
 */
export function NumberField({
  meta,
  value,
  onChange,
  step = 1,
  min,
  max,
  nullable = false,
  placeholder,
  disabled,
  status,
}: {
  meta: FieldMeta;
  value: number | null;
  onChange: (v: number | null) => void;
  step?: number;
  min?: number;
  max?: number;
  nullable?: boolean;
  placeholder?: string;
  disabled?: boolean;
  status?: "ok" | "warn";
}) {
  const text = value === null || !Number.isFinite(value as number) ? "" : String(value);
  const [draft, setDraft] = useState(text);
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) setDraft(text);
  }, [text]);

  const commit = () => {
    const trimmed = draft.trim();
    if (trimmed === "") {
      if (nullable) {
        onChange(null);
        setDraft("");
      } else {
        setDraft(text);
      }
      return;
    }
    const parsed = parseFloat(trimmed);
    if (Number.isFinite(parsed)) {
      let v = parsed;
      if (min !== undefined) v = Math.max(min, v);
      if (max !== undefined) v = Math.min(max, v);
      if (v !== value) onChange(v);
      setDraft(String(v));
    } else {
      setDraft(text);
    }
  };

  return (
    <div className={`tp-field ${status ? `tp-field-${status}` : ""}`}>
      <FieldLabel meta={meta} />
      <input
        type="number"
        className="tp-input"
        step={step}
        min={min}
        max={max}
        disabled={disabled}
        placeholder={placeholder}
        value={draft}
        onFocus={() => {
          focused.current = true;
        }}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          focused.current = false;
          commit();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          else if (e.key === "Escape") {
            setDraft(text);
            e.currentTarget.blur();
          }
        }}
      />
    </div>
  );
}
