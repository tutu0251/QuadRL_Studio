import { useEffect, useRef, useState } from "react";

/**
 * Text <input> that edits a local draft while focused and only commits
 * (onCommit) on blur or Enter. Avoids a network round-trip per keystroke for
 * fields backed by server state. Escape reverts to the committed value.
 */
export function TextField({
  value,
  onCommit,
  className,
  title,
  placeholder,
}: {
  value: string;
  onCommit: (v: string) => void;
  className?: string;
  title?: string;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState(value);
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) setDraft(value);
  }, [value]);

  const commit = () => {
    if (draft !== value) onCommit(draft);
  };

  return (
    <input
      className={className}
      title={title}
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
          setDraft(value);
          e.currentTarget.blur();
        }
      }}
    />
  );
}
