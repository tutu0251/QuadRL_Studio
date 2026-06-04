import { useState } from "react";
import { copyToClipboard } from "../utils/clipboard";

type Props = {
  command: string | null | undefined;
  loading?: boolean;
};

export function CommandPreview({ command, loading }: Props) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  if (loading) {
    return <pre className="command-preview loading">Loading command…</pre>;
  }
  if (!command) return null;

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

  return (
    <div className="command-preview-wrap">
      <pre className="command-preview">{command}</pre>
      <button type="button" className="btn tiny command-copy" onClick={() => void copy()}>
        {copied ? "Copied" : copyFailed ? "Copy failed" : "Copy"}
      </button>
    </div>
  );
}
