import { useEffect, useRef, useState } from "react";

/**
 * Bare numeric <input> that edits a local string draft while focused and only
 * commits (parse + onCommit) on blur or Enter. Avoids a network round-trip /
 * store write per keystroke and lets you type intermediate states like "-",
 * "0.", or "0.05" without the value snapping back to source state.
 */
export function NumericInput({
  value,
  onCommit,
  step = 0.01,
  min,
  max,
  disabled,
  className,
  title,
  "aria-label": ariaLabel,
}: {
  value: number;
  onCommit: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
  disabled?: boolean;
  className?: string;
  title?: string;
  "aria-label"?: string;
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
      let v = parsed;
      if (min !== undefined) v = Math.max(min, v);
      if (max !== undefined) v = Math.min(max, v);
      if (v !== value) onCommit(v);
      setDraft(String(v));
    } else {
      setDraft(String(safe));
    }
  };

  return (
    <input
      type="number"
      className={className}
      step={step}
      min={min}
      max={max}
      disabled={disabled}
      title={title}
      aria-label={ariaLabel}
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
  );
}
