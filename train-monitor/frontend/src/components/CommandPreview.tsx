import { useRef, useState } from "react";
import { copyToClipboard } from "../utils/clipboard";

type Props = {
  command: string | null | undefined;
  loading?: boolean;
};

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden focusable="false">
      <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
      <path
        d="M5 15V5a2 2 0 0 1 2-2h10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/**
 * Compact copy-the-command control: a small icon button shown beside its main
 * action button. Hovering (or focusing) reveals the full shell command in a
 * popover; clicking copies it to the clipboard. The popover is fixed-positioned
 * off the button's bounding rect so it is never clipped by panel overflow.
 */
export function CommandPreview({ command, loading }: Props) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  if (loading) {
    return (
      <span className="command-copy">
        <button type="button" className="btn tiny command-copy-btn" disabled aria-label="Loading command">
          <span className="command-copy-dots">⋯</span>
        </button>
      </span>
    );
  }
  if (!command) return null;

  const show = () => {
    const r = btnRef.current?.getBoundingClientRect();
    if (r) setPos({ left: r.left + r.width / 2, top: r.top });
  };
  const hide = () => setPos(null);

  const copy = async () => {
    const ok = await copyToClipboard(command);
    if (ok) {
      setCopyFailed(false);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
      return;
    }
    setCopyFailed(true);
    window.setTimeout(() => setCopyFailed(false), 2500);
  };

  const label = copied ? "Command copied" : copyFailed ? "Copy failed" : "Copy command";

  return (
    <span className="command-copy" onMouseEnter={show} onMouseLeave={hide}>
      <button
        ref={btnRef}
        type="button"
        className={`btn tiny command-copy-btn${copied ? " ok" : ""}${copyFailed ? " err" : ""}`}
        onClick={() => void copy()}
        onFocus={show}
        onBlur={hide}
        aria-label={label}
      >
        {copied ? "✓" : copyFailed ? "✕" : <CopyIcon />}
      </button>
      {pos && (
        <span className="command-popover" role="tooltip" style={{ left: pos.left, top: pos.top }}>
          <code>{command}</code>
        </span>
      )}
    </span>
  );
}
