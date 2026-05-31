import type { RlTrainerModel } from "@rl-trainer-model";

export function formatTimesteps(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

export function machineTier(ramGb: number): "low" | "mid" | "high" | "workstation" {
  if (ramGb < 8) return "low";
  if (ramGb < 16) return "mid";
  if (ramGb < 32) return "high";
  return "workstation";
}

export function enabledRewardCount(model: RlTrainerModel): number {
  return model.rewardTerms.filter((t) => t.enabled).length;
}
