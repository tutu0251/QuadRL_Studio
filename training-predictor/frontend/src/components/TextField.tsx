import { useEffect, useRef, useState } from "react";
import type { FieldMeta } from "../labels";
import { FieldLabel } from "./FieldLabel";

/** Text input with a friendly label; commits an empty box as `null` when `nullable`. */
export function TextField({
  meta,
  value,
  onChange,
  placeholder,
  disabled,
  nullable = false,
}: {
  meta: FieldMeta;
  value: string | null;
  onChange: (v: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  nullable?: boolean;
}) {
  const text = value ?? "";
  const [draft, setDraft] = useState(text);
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) setDraft(text);
  }, [text]);

  const commit = () => {
    const trimmed = draft.trim();
    if (trimmed === "" && nullable) {
      onChange(null);
      setDraft("");
      return;
    }
    onChange(trimmed);
    setDraft(trimmed);
  };

  return (
    <div className="tp-field">
      <FieldLabel meta={meta} />
      <input
        type="text"
        className="tp-input"
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
