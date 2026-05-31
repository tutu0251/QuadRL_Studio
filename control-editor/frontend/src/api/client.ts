import type { ControlModel, TrainingProfile, ValidationResult } from "@control-model";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8002";

export type ExportTaskResult = {
  urdf?: string;
  controllers?: string;
  gains?: string;
  exportValidation?: ValidationResult;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<T>;
}

export const wsLogsUrl = () => {
  const u = new URL(BASE);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  return `${u.origin}/ws/logs`;
};

export const api = {
  health: () => req<{ status: string }>("/api/health"),
  listProjects: () =>
    req<{
      projects: string[];
      active: string | null;
      details: { name: string; hasPhyUrdf: boolean; hasControl: boolean }[];
    }>("/api/projects"),
  loadProject: (name: string) =>
    req<{ project: string; model: ControlModel; hasControl: boolean }>(
      `/api/projects/${name}/load`,
      { method: "POST" }
    ),
  importPhy: (name: string) =>
    req<{ project: string; model: ControlModel }>(`/api/projects/${name}/import`, {
      method: "POST",
    }),
  getModel: (name: string) => req<ControlModel>(`/api/projects/${name}/model`),
  setProfile: (name: string, trainingProfile: TrainingProfile) =>
    req<ControlModel>(`/api/projects/${name}/profile`, {
      method: "PATCH",
      body: JSON.stringify({ trainingProfile }),
    }),
  updateJoint: (name: string, jointName: string, body: Record<string, number | boolean>) =>
    req<ControlModel>(`/api/projects/${name}/joints/${encodeURIComponent(jointName)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  regenerate: (name: string) =>
    req<ControlModel>(`/api/projects/${name}/regenerate`, { method: "POST" }),
  validate: (name: string) =>
    req<ValidationResult>(`/api/projects/${name}/validate`, { method: "POST" }),
  validateExport: (name: string) =>
    req<{ task_id: string }>(`/api/projects/${name}/validate/export`, { method: "POST" }),
  validateGazeboAsync: (name: string) =>
    req<{ task_id: string }>(`/api/projects/${name}/validate/gazebo/async`, { method: "POST" }),
  exportRos2Control: (name: string) =>
    req<{ task_id: string }>(`/api/projects/${name}/export/ros2_control`, { method: "POST" }),
  getTask: (taskId: string) =>
    req<{ task_id: string; status: string; result?: ExportTaskResult }>(
      `/api/tasks/${taskId}`
    ),
};
