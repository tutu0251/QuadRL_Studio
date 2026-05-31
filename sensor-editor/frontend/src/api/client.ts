import type { SensorKind, SensorModel, ValidationResult } from "@sensor-model";

export type SensorCreate = {
  kind: SensorKind;
  name?: string;
  parentLink: string;
  enabled?: boolean;
  pose?: SensorModel["sensors"][0]["pose"];
  rosTopic?: string;
  updateRate?: number;
  imu?: SensorModel["sensors"][0]["imu"];
  contact?: SensorModel["sensors"][0]["contact"];
  lidar?: SensorModel["sensors"][0]["lidar"];
};

export type SensorUpdate = Partial<
  Omit<SensorCreate, "kind" | "parentLink"> & { parentLink?: string }
>;

const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8003";

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
      details: { name: string; hasCtrlUrdf: boolean; hasSensor: boolean }[];
    }>("/api/projects"),
  loadProject: (name: string) =>
    req<{ project: string; model: SensorModel; hasSensor: boolean }>(
      `/api/projects/${name}/load`,
      { method: "POST" }
    ),
  importCtrl: (name: string) =>
    req<{ project: string; model: SensorModel }>(`/api/projects/${name}/import/ctrl`, {
      method: "POST",
    }),
  bootstrapQuadruped: (name: string) =>
    req<SensorModel>(`/api/projects/${name}/bootstrap/quadruped`, { method: "POST" }),
  getModel: (name: string) => req<SensorModel>(`/api/projects/${name}/model`),
  updateTopicConfig: (
    name: string,
    body: { topicPrefix?: string; gzModelName?: string; updateRateDefault?: number }
  ) =>
    req<SensorModel>(`/api/projects/${name}/topic-config`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  addSensor: (name: string, body: SensorCreate) =>
    req<SensorModel>(`/api/projects/${name}/sensors`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateSensor: (name: string, sensorId: string, body: SensorUpdate) =>
    req<SensorModel>(`/api/projects/${name}/sensors/${encodeURIComponent(sensorId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteSensor: (name: string, sensorId: string) =>
    req<SensorModel>(`/api/projects/${name}/sensors/${encodeURIComponent(sensorId)}`, {
      method: "DELETE",
    }),
  validate: (name: string) =>
    req<ValidationResult>(`/api/projects/${name}/validate`, { method: "POST" }),
  exportRl: (name: string) =>
    req<{ task_id: string }>(`/api/projects/${name}/export/rl`, { method: "POST" }),
  getTask: (taskId: string) =>
    req<{
      task_id: string;
      status: string;
      result?: Record<string, unknown> & { sensorValidation?: ValidationResult };
    }>(`/api/tasks/${taskId}`),
};

export type { SensorKind };
