import { getProceduralObservationEntry } from "./observationCatalog";

/** Minimal fields needed for dimension math (avoids circular import with index). */
export interface ObservationTermDimInput {
  id: string;
  source: "procedural" | "sensor";
  kind: string;
  category?: string;
  label?: string;
  key?: string;
  fields?: string[];
  enabled: boolean;
  available: boolean;
}

/** Context for resolving procedural dims (n_joints) and sensor field layouts. */
export interface ObservationDimContext {
  nJoints: number;
}

export interface ObservationVectorSegment {
  termId: string;
  label: string;
  category: string;
  source: ObservationTermDimInput["source"];
  kind: string;
  dim: number;
  enabled: boolean;
  available: boolean;
  /** Index in the policy vector; null when term is not included. */
  startIndex: number | null;
}

export interface ObservationVectorBreakdown {
  nJoints: number;
  totalDim: number;
  enabledTermCount: number;
  availableTermCount: number;
  categoryDims: Record<string, number>;
  segments: ObservationVectorSegment[];
}

/** Per exported sensor field (matches training/quadrl_env/sensor_packing.py). */
export function computeObservationFieldDim(kind: string, field: string): number {
  const k = (kind || "").toLowerCase();
  if (k === "contact") return 1;
  if (k === "odom") return 1;
  if (k === "lidar") return field === "ranges" ? 16 : 1;
  return 3;
}

/** Mirrors training/quadrl_env/observations.py::_term_dim */
export function computeObservationTermDim(
  term: Pick<ObservationTermDimInput, "id" | "source" | "kind"> & {
    fields?: string[];
  },
  ctx: ObservationDimContext
): number {
  const n = Math.max(1, ctx.nJoints);
  if (term.source === "procedural") {
    if (
      term.id === "joint_positions" ||
      term.id === "joint_velocities" ||
      term.id === "last_actions"
    ) {
      return n;
    }
    if (term.id === "commands") return 5;
    if (
      term.id === "base_lin_vel" ||
      term.id === "base_ang_vel" ||
      term.id === "projected_gravity"
    ) {
      return 3;
    }
    return 1;
  }

  const kind = (term.kind || "").toLowerCase();
  const fields = term.fields ?? [];
  if (kind === "contact") return Math.max(1, fields.length || 1);
  if (kind === "lidar") return 16;
  if (kind === "odom") return Math.max(1, fields.length || 1);
  if (fields.length === 0) return 3;
  return Math.max(3, fields.reduce((sum, f) => sum + computeObservationFieldDim(kind, f), 0));
}

export function formatObservationTermDimLabel(
  term: Pick<ObservationTermDimInput, "id" | "source" | "kind"> & { fields?: string[] },
  ctx: ObservationDimContext
): string {
  const dim = computeObservationTermDim(term, ctx);
  const entry = term.source === "procedural" ? getProceduralObservationEntry(term.id) : undefined;
  const hint = entry?.dimsHint;
  if (hint === "n_joints" || hint === "n_actions") {
    return `${dim} (${ctx.nJoints}×1)`;
  }
  if (hint) return `${dim} (${hint})`;
  return String(dim);
}

export function buildObservationVectorBreakdown(
  terms: ObservationTermDimInput[],
  ctx: ObservationDimContext
): ObservationVectorBreakdown {
  const segments: ObservationVectorSegment[] = [];
  const categoryDims: Record<string, number> = {
    state: 0,
    command: 0,
    sensor: 0,
  };
  let offset = 0;
  let totalDim = 0;
  let enabledTermCount = 0;
  const availableTermCount = terms.filter((t) => t.available).length;

  for (const term of terms) {
    const dim = computeObservationTermDim(term, ctx);
    const inVector = term.enabled && term.available;
    const startIndex = inVector ? offset : null;
    if (inVector) {
      offset += dim;
      totalDim += dim;
      enabledTermCount += 1;
      const cat = term.category || "sensor";
      categoryDims[cat] = (categoryDims[cat] ?? 0) + dim;
    }
    segments.push({
      termId: term.id,
      label: (term.label || term.key || term.id) as string,
      category: term.category || "sensor",
      source: term.source,
      kind: term.kind,
      dim,
      enabled: term.enabled,
      available: term.available,
      startIndex,
    });
  }

  return {
    nJoints: ctx.nJoints,
    totalDim,
    enabledTermCount,
    availableTermCount,
    categoryDims,
    segments,
  };
}
