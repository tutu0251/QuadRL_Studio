import type { FieldMeta } from "../labels";

/**
 * The shared label primitive: a friendly Title-Case name on top, the raw backend
 * key as a small mono sublabel underneath, and an info affordance carrying the hint.
 * Every field in the app routes its label through here so naming stays consistent.
 */
export function FieldLabel({ meta }: { meta: FieldMeta }) {
  return (
    <span className="tp-fieldlabel">
      <span className="tp-fieldlabel-main" title={meta.hint}>
        {meta.label}
        {meta.hint ? (
          <span className="tp-hint" title={meta.hint} aria-label={meta.hint}>
            ⓘ
          </span>
        ) : null}
      </span>
      {meta.code ? <span className="tp-fieldlabel-code">{meta.code}</span> : null}
    </span>
  );
}
