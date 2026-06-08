import { useEffect, useRef, useState } from "react";

interface Props {
  value: number;
  onCommit: (value: number) => void;
  step?: number;
  title?: string;
  className?: string;
}

/**
 * Number input that edits a local string while focused and only commits
 * (parses + fires onCommit) on blur or Enter. This avoids a network
 * round-trip per keystroke and lets you freely type intermediate states
 * like "-", "0.", or "0.05" without the value snapping back to server state.
 */
export function NumberField({ value, onCommit, step = 0.01, title, className }: Props) {
  const [draft, setDraft] = useState<string>(String(value));
  const focused = useRef(false);

  // Sync from props when the field is not being edited (external updates).
  useEffect(() => {
    if (!focused.current) setDraft(String(value));
  }, [value]);

  const commit = () => {
    const parsed = parseFloat(draft);
    if (Number.isFinite(parsed)) {
      if (parsed !== value) onCommit(parsed);
    } else {
      setDraft(String(value)); // revert invalid/empty input
    }
  };

  return (
    <input
      type="number"
      step={step}
      title={title}
      className={className}
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
        if (e.key === "Enter") {
          e.currentTarget.blur();
        } else if (e.key === "Escape") {
          setDraft(String(value));
          e.currentTarget.blur();
        }
      }}
    />
  );
}
