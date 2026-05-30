import type { MachineProfile, PpoHyperparams } from "@ppo-model";

export function rolloutSize(p: PpoHyperparams): number {
  return p.nSteps * p.numEnvs;
}

export function batchDividesRollout(p: PpoHyperparams): boolean {
  const r = rolloutSize(p);
  return r > 0 && r % p.batchSize === 0;
}

export function resolvedDevice(
  p: PpoHyperparams,
  machine: MachineProfile | null | undefined
): "cuda" | "cpu" {
  if (p.device === "cuda") return "cuda";
  if (p.device === "cpu") return "cpu";
  return machine?.gpuAvailable ? "cuda" : "cpu";
}

export function machineTier(ramGb: number): "low" | "mid" | "high" | "workstation" {
  if (ramGb < 8) return "low";
  if (ramGb < 16) return "mid";
  if (ramGb < 32) return "high";
  return "workstation";
}

export function formatTimesteps(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}
