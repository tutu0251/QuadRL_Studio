import { useEffect, useRef, useState } from "react";

/**
 * Numeric <input> that edits a local string draft while focused and only
 * commits (parse + onCommit) on blur or Enter. Lets you type intermediate
 * states like "-", "0.", or "0.05" without the value snapping back, and avoids
 * coercing partial input to 0 on every keystroke.
 *
 * When `nullable` is set, an empty field commits `null`; otherwise an empty or
 * invalid field reverts to the last committed value.
 */
export function NumericInput({
  value,
  onCommit,
  step = 0.01,
  min,
  disabled,
  nullable = false,
}: {
  value: number | null;
  onCommit: (v: number | null) => void;
  step?: number;
  min?: number;
  disabled?: boolean;
  nullable?: boolean;
}) {
  const display = value === null || value === undefined ? "" : String(value);
  const [draft, setDraft] = useState(display);
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) setDraft(display);
  }, [display]);

  const commit = () => {
    const raw = draft.trim();
    if (raw === "") {
      if (nullable) {
        if (value !== null) onCommit(null);
        setDraft("");
      } else {
        setDraft(display);
      }
      return;
    }
    const parsed = parseFloat(raw);
    if (Number.isFinite(parsed)) {
      const v = min !== undefined ? Math.max(min, parsed) : parsed;
      if (v !== value) onCommit(v);
      setDraft(String(v));
    } else {
      setDraft(display);
    }
  };

  return (
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
          setDraft(display);
          e.currentTarget.blur();
        }
      }}
    />
  );
}
