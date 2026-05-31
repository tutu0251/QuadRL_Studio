/** Reward/penalty catalog — mirrors backend planner/reward_catalog.py */

export interface RewardParamRange {
  key: string;
  recommended: number;
  min: number;
  max: number;
  step: number;
}

export interface RewardCatalogEntry {
  id: string;
  type: "reward" | "penalty";
  category: string;
  recommendedWeight: number;
  params: RewardParamRange[];
}

export const REWARD_CATALOG: RewardCatalogEntry[] = [
  { id: "alive", type: "reward", category: "survival", recommendedWeight: 0.25, params: [] },
  {
    id: "upright",
    type: "reward",
    category: "orientation",
    recommendedWeight: 0.8,
    params: [{ key: "sigma", recommended: 0.12, min: 0.03, max: 0.4, step: 0.01 }],
  },
  {
    id: "height",
    type: "reward",
    category: "height",
    recommendedWeight: 1.0,
    params: [
      { key: "target_height", recommended: 0.35, min: 0.2, max: 0.5, step: 0.01 },
      { key: "sigma", recommended: 0.06, min: 0.02, max: 0.2, step: 0.01 },
    ],
  },
  {
    id: "posture",
    type: "reward",
    category: "posture",
    recommendedWeight: 0.5,
    params: [{ key: "sigma", recommended: 0.15, min: 0.05, max: 0.5, step: 0.01 }],
  },
  {
    id: "contact",
    type: "reward",
    category: "contact",
    recommendedWeight: 0.35,
    params: [
      { key: "min_contacts", recommended: 2, min: 1, max: 4, step: 1 },
      { key: "sigma", recommended: 0.2, min: 0.05, max: 0.6, step: 0.01 },
    ],
  },
  {
    id: "forward_tracking",
    type: "reward",
    category: "velocity",
    recommendedWeight: 1.0,
    params: [{ key: "sigma", recommended: 0.22, min: 0.08, max: 0.6, step: 0.01 }],
  },
  {
    id: "lateral_tracking",
    type: "reward",
    category: "velocity",
    recommendedWeight: 0.4,
    params: [{ key: "sigma", recommended: 0.18, min: 0.06, max: 0.5, step: 0.01 }],
  },
  {
    id: "yaw_tracking",
    type: "reward",
    category: "velocity",
    recommendedWeight: 0.5,
    params: [{ key: "sigma", recommended: 0.2, min: 0.08, max: 0.55, step: 0.01 }],
  },
  {
    id: "diagonal_balance",
    type: "reward",
    category: "gait",
    recommendedWeight: 0.25,
    params: [{ key: "sigma", recommended: 0.15, min: 0.05, max: 0.45, step: 0.01 }],
  },
  {
    id: "air_time",
    type: "reward",
    category: "gait",
    recommendedWeight: 0.15,
    params: [
      { key: "target_air_time", recommended: 0.12, min: 0.04, max: 0.35, step: 0.01 },
      { key: "sigma", recommended: 0.08, min: 0.02, max: 0.25, step: 0.01 },
    ],
  },
  {
    id: "foot_clearance",
    type: "reward",
    category: "gait",
    recommendedWeight: 0.2,
    params: [
      { key: "min_clearance", recommended: 0.04, min: 0.01, max: 0.12, step: 0.005 },
      { key: "sigma", recommended: 0.03, min: 0.01, max: 0.1, step: 0.01 },
    ],
  },
  {
    id: "angular_velocity",
    type: "penalty",
    category: "velocity",
    recommendedWeight: -0.25,
    params: [{ key: "sigma", recommended: 0.15, min: 0.05, max: 0.5, step: 0.01 }],
  },
  {
    id: "linear_velocity",
    type: "penalty",
    category: "velocity",
    recommendedWeight: -0.35,
    params: [{ key: "sigma", recommended: 0.1, min: 0.03, max: 0.35, step: 0.01 }],
  },
  {
    id: "z_velocity",
    type: "penalty",
    category: "velocity",
    recommendedWeight: -0.2,
    params: [{ key: "sigma", recommended: 0.08, min: 0.02, max: 0.3, step: 0.01 }],
  },
  {
    id: "joint_velocity",
    type: "penalty",
    category: "energy",
    recommendedWeight: -0.00015,
    params: [{ key: "sigma", recommended: 1.0, min: 0.1, max: 5.0, step: 0.1 }],
  },
  {
    id: "action_velocity",
    type: "penalty",
    category: "action_smoothness",
    recommendedWeight: -0.03,
    params: [{ key: "sigma", recommended: 0.12, min: 0.04, max: 0.4, step: 0.01 }],
  },
  {
    id: "action_rate",
    type: "penalty",
    category: "action_smoothness",
    recommendedWeight: -0.05,
    params: [{ key: "sigma", recommended: 0.1, min: 0.03, max: 0.35, step: 0.01 }],
  },
  {
    id: "posture_penalty",
    type: "penalty",
    category: "posture",
    recommendedWeight: -0.4,
    params: [{ key: "sigma", recommended: 0.1, min: 0.03, max: 0.4, step: 0.01 }],
  },
  {
    id: "target_posture",
    type: "penalty",
    category: "posture",
    recommendedWeight: -0.35,
    params: [{ key: "sigma", recommended: 0.12, min: 0.04, max: 0.45, step: 0.01 }],
  },
  {
    id: "smoothness",
    type: "penalty",
    category: "action_smoothness",
    recommendedWeight: -0.05,
    params: [{ key: "sigma", recommended: 0.1, min: 0.03, max: 0.35, step: 0.01 }],
  },
  {
    id: "contact_balance",
    type: "penalty",
    category: "contact",
    recommendedWeight: -0.15,
    params: [{ key: "sigma", recommended: 0.2, min: 0.05, max: 0.6, step: 0.01 }],
  },
  {
    id: "contact_switch",
    type: "penalty",
    category: "contact",
    recommendedWeight: -0.1,
    params: [
      { key: "max_switches_per_step", recommended: 2, min: 1, max: 4, step: 1 },
      { key: "sigma", recommended: 0.25, min: 0.08, max: 0.7, step: 0.01 },
    ],
  },
  {
    id: "target_like",
    type: "penalty",
    category: "tracking",
    recommendedWeight: -0.2,
    params: [{ key: "sigma", recommended: 0.18, min: 0.06, max: 0.5, step: 0.01 }],
  },
  {
    id: "stumble",
    type: "penalty",
    category: "contact",
    recommendedWeight: -0.12,
    params: [
      { key: "threshold", recommended: 35, min: 10, max: 120, step: 1 },
      { key: "sigma", recommended: 15, min: 5, max: 50, step: 1 },
    ],
  },
  {
    id: "slip",
    type: "penalty",
    category: "contact",
    recommendedWeight: -0.1,
    params: [
      { key: "threshold", recommended: 0.25, min: 0.05, max: 0.8, step: 0.01 },
      { key: "sigma", recommended: 0.12, min: 0.04, max: 0.4, step: 0.01 },
    ],
  },
  {
    id: "zmp",
    type: "penalty",
    category: "stability",
    recommendedWeight: -0.15,
    params: [
      { key: "margin", recommended: 0.02, min: 0.005, max: 0.08, step: 0.005 },
      { key: "sigma", recommended: 0.03, min: 0.01, max: 0.12, step: 0.01 },
    ],
  },
];

const catalogById = new Map(REWARD_CATALOG.map((e) => [e.id, e]));

export function getRewardParamRange(termId: string, paramKey: string): RewardParamRange | undefined {
  return catalogById.get(termId)?.params.find((p) => p.key === paramKey);
}

export function getRewardCatalogEntry(termId: string): RewardCatalogEntry | undefined {
  return catalogById.get(termId);
}

export function clampRewardParam(termId: string, paramKey: string, value: number): number {
  const spec = getRewardParamRange(termId, paramKey);
  if (!spec) return value;
  return Math.max(spec.min, Math.min(spec.max, value));
}
