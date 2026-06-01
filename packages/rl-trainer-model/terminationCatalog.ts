/** Termination condition catalog — mirrors backend planner/termination_catalog.py */

export interface TerminationParamRange {
  key: string;
  recommended: number;
  min: number;
  max: number;
  step: number;
}

export interface TerminationCatalogEntry {
  id: string;
  label: string;
  category: string;
  params: TerminationParamRange[];
}

export const TERMINATION_CATALOG: TerminationCatalogEntry[] = [
  {
    id: "foot_slip_contact_loss",
    label: "Foot slip / contact loss",
    category: "contact",
    params: [
      { key: "slip_threshold", recommended: 0.25, min: 0.05, max: 1.0, step: 0.01 },
      { key: "min_contacts", recommended: 1, min: 1, max: 4, step: 1 },
      { key: "contact_loss_steps", recommended: 3, min: 1, max: 30, step: 1 },
    ],
  },
  {
    id: "base_linear_velocity_limit",
    label: "Base linear velocity limit",
    category: "velocity",
    params: [{ key: "max_lin_vel", recommended: 3.0, min: 0.5, max: 8.0, step: 0.1 }],
  },
  {
    id: "base_angular_velocity_limit",
    label: "Base angular velocity limit",
    category: "velocity",
    params: [{ key: "max_ang_vel", recommended: 5.0, min: 1.0, max: 15.0, step: 0.1 }],
  },
  {
    id: "joint_limits_self_collision",
    label: "Joint limits / self-collision",
    category: "safety",
    params: [{ key: "limit_margin", recommended: 0.05, min: 0.01, max: 0.2, step: 0.005 }],
  },
  {
    id: "energy_torque_safety",
    label: "Energy / torque safety",
    category: "energy",
    params: [
      { key: "max_joint_torque", recommended: 80, min: 10, max: 200, step: 1 },
      { key: "max_joint_power", recommended: 500, min: 50, max: 2000, step: 10 },
    ],
  },
  {
    id: "height_deviation_terrain_contact",
    label: "Height deviation / terrain contact",
    category: "height",
    params: [
      { key: "max_height_deviation", recommended: 0.12, min: 0.03, max: 0.4, step: 0.01 },
      { key: "min_terrain_contacts", recommended: 1, min: 0, max: 4, step: 1 },
    ],
  },
  {
    id: "reward_anomaly",
    label: "Excessive episode reward anomaly",
    category: "monitoring",
    params: [
      { key: "max_step_reward", recommended: 5.0, min: 0.5, max: 50, step: 0.5 },
      { key: "cumulative_threshold", recommended: 100, min: 10, max: 500, step: 5 },
    ],
  },
];

const catalogById = new Map(TERMINATION_CATALOG.map((e) => [e.id, e]));

export function getTerminationCatalogEntry(termId: string): TerminationCatalogEntry | undefined {
  return catalogById.get(termId);
}

export function getTerminationParamRange(
  termId: string,
  paramKey: string
): TerminationParamRange | undefined {
  return catalogById.get(termId)?.params.find((p) => p.key === paramKey);
}

export function clampTerminationParam(termId: string, paramKey: string, value: number): number {
  const spec = getTerminationParamRange(termId, paramKey);
  if (!spec) return value;
  return Math.max(spec.min, Math.min(spec.max, value));
}
