export function ParamHint({ text }: { text?: string }) {
  if (!text) return null;
  return (
    <span className="param-hint-icon" title={text} aria-label={text}>
      ⓘ
    </span>
  );
}

export function FieldLabel({ label, hint }: { label: string; hint?: string }) {
  return (
    <span className="field-label-row">
      <span className="field-label" title={hint}>
        {label}
      </span>
      <ParamHint text={hint} />
    </span>
  );
}
