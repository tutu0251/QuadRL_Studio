import type { StudyState } from "../api/types";
import { STATE_LABELS } from "../labels";

/** A pill showing the study lifecycle state, colored by the design-system tokens. */
export function StatusBadge({ state }: { state: StudyState | "idle" }) {
  const label = state === "idle" ? "Idle" : STATE_LABELS[state] ?? state;
  return (
    <span className={`tp-badge tp-badge-${state}`}>
      {state === "running" ? <span className="tp-badge-pulse" /> : null}
      {label}
    </span>
  );
}
