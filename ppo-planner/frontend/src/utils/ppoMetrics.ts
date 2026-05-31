import type { PpoHyperparams, ParallelConfig, ExportConfigFormat } from "@ppo-model";
import { EXPORT_FORMAT_OPTIONS } from "@ppo-model";

export function rolloutSize(p: PpoHyperparams, numEnvs: number): number {
  return p.nSteps * numEnvs;
}

export function batchDividesRollout(p: PpoHyperparams, numEnvs: number): boolean {
  const r = rolloutSize(p, numEnvs);
  return r > 0 && r % p.batchSize === 0;
}

export function resolvedDevice(
  p: PpoHyperparams,
  machine: { gpuAvailable?: boolean } | null | undefined
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

export function exportConfigFilename(projectName: string, format: ExportConfigFormat): string {
  const opt = EXPORT_FORMAT_OPTIONS.find((o) => o.id === format);
  const suffix = opt?.filenameSuffix ?? "_config.yaml";
  return `ppo_${projectName}${suffix}`;
}

export function exportConfigFilenames(
  projectName: string,
  formats: ExportConfigFormat[]
): string[] {
  return formats.map((f) => exportConfigFilename(projectName, f));
}

export function exportFormatsSummary(formats: ExportConfigFormat[]): string {
  if (!formats.length) return "none";
  if (formats.length === 1) return formats[0].toUpperCase();
  return formats.map((f) => f.replace("_", " ").toUpperCase()).join(" + ");
}

export function exportToolbarLabel(formats: ExportConfigFormat[]): string {
  if (!formats.length) return "Export";
  if (formats.length === 1) {
    const id = formats[0];
    if (id === "yaml") return "Export YAML";
    if (id === "toml") return "Export TOML";
    if (id === "json_min") return "Export JSON (min)";
    return "Export JSON";
  }
  return `Export (${formats.length} files)`;
}

export function checkpointSummary(
  ckpt: { enabled: boolean; frequency: string; directory: string; filenameTemplate: string }
): string {
  if (!ckpt.enabled) return "disabled";
  return `${ckpt.directory}/${ckpt.filenameTemplate} · ${ckpt.frequency.replace("_", " ")}`;
}

export function bestModelSummary(
  best: { enabled: boolean; metric: string; filename: string; directory: string }
): string {
  if (!best.enabled) return "disabled";
  return `${best.directory}/${best.filename}.zip · ${best.metric.replace(/_/g, " ")}`;
}

export function formatTimesteps(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

export function parallelSummary(par: ParallelConfig): string {
  const proc =
    par.vecEnvType === "subproc" && par.nProc != null ? ` · n_proc ${par.nProc}` : "";
  return `${par.numEnvs} env${par.numEnvs === 1 ? "" : "s"} · ${par.vecEnvType}${proc}`;
}

export function maxRecommendedEnvs(
  machine: { ramGb: number; cpuCountPhysical: number; gpuAvailable: boolean; vramGb: number; cpuCountLogical: number } | null | undefined
): number {
  if (!machine) return 8;
  const physical = Math.max(1, machine.cpuCountPhysical);
  const ram = machine.ramGb || 8;
  let cap: number;
  if (ram < 8) cap = 1;
  else if (ram < 16) cap = Math.min(2, Math.max(1, Math.floor(physical / 4)));
  else if (ram < 32) cap = Math.min(4, Math.max(1, Math.floor(physical / 2)));
  else cap = Math.min(8, Math.max(2, Math.floor(physical / 2)));
  if (machine.gpuAvailable && machine.vramGb >= 12) {
    cap = Math.min(8, Math.max(cap, Math.min(4, Math.floor(machine.cpuCountLogical / 2))));
  }
  if (!machine.gpuAvailable) {
    cap = Math.min(cap, Math.max(1, Math.floor(physical / 2)));
  }
  return Math.max(1, cap);
}
