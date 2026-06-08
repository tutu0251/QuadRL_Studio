import { useEffect, useRef, useState } from "react";
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
  const safe = Number.isFinite(value) ? value : 0;
  const [draft, setDraft] = useState(String(safe));
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) setDraft(String(safe));
  }, [safe]);

  const commit = () => {
    const parsed = parseFloat(draft);
    if (Number.isFinite(parsed)) {
      const v = min !== undefined ? Math.max(min, parsed) : parsed;
      if (v !== value) onChange(v);
      setDraft(String(v));
    } else {
      setDraft(String(safe));
    }
  };

  return (
    <div className="inspector-row">
      <FieldLabel label={label} hint={hint} />
      <input
        type="number"
        step={step}
        min={min}
        disabled={disabled}
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
            setDraft(String(safe));
            e.currentTarget.blur();
          }
        }}
      />
    </div>
  );
}
