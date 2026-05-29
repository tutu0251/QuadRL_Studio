const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

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
      details: { name: string; hasGeoUrdf: boolean; hasPhysics: boolean }[];
    }>("/api/projects"),
  loadProject: (name: string) =>
    req<{ project: string; model: import("@robot-model").RobotModel; hasPhysics: boolean }>(
      `/api/projects/${name}/load`,
      { method: "POST" }
    ),
  importGeo: (name: string) =>
    req<{ project: string; model: import("@robot-model").RobotModel }>(
      `/api/projects/${name}/import`,
      { method: "POST" }
    ),
  getModel: (name: string) => req<import("@robot-model").RobotModel>(`/api/projects/${name}/model`),
  updateInertial: (project: string, linkId: string, body: unknown) =>
    req(`/api/projects/${project}/links/${linkId}/inertial`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  updateFriction: (project: string, linkId: string, body: unknown) =>
    req(`/api/projects/${project}/links/${linkId}/friction`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  setFoot: (project: string, linkId: string, isFoot: boolean) =>
    req(`/api/projects/${project}/links/${linkId}/foot?is_foot=${isFoot}`, { method: "PATCH" }),
  updateDynamics: (project: string, jointId: string, body: unknown) =>
    req(`/api/projects/${project}/joints/${jointId}/dynamics`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  estimateLink: (project: string, linkId: string, density = 1000) =>
    req(`/api/projects/${project}/links/${linkId}/estimate`, {
      method: "POST",
      body: JSON.stringify({ density }),
    }),
  estimateAll: (project: string, density = 1000) =>
    req(`/api/projects/${project}/estimate-all`, {
      method: "POST",
      body: JSON.stringify({ density }),
    }),
  validate: (project: string) =>
    req<import("@robot-model").ValidationResult>(`/api/projects/${project}/validate`, { method: "POST" }),
  exportUrdf: (project: string) =>
    req<{ task_id: string }>(`/api/projects/${project}/export/urdf`, { method: "POST" }),
  exportGazebo: (project: string) =>
    req<{ task_id: string }>(`/api/projects/${project}/export/gazebo`, { method: "POST" }),
  exportBoth: (project: string) =>
    req<{ task_id: string }>(`/api/projects/${project}/export/both`, { method: "POST" }),
  getTask: (taskId: string) =>
    req<{ task_id: string; status: string; result?: Record<string, string> }>(`/api/tasks/${taskId}`),
  gazeboPreview: (project: string) =>
    req<{ sdf: string; command: string; exists: boolean }>(`/api/projects/${project}/gazebo-preview`),
  robotCom: (project: string) => req<{ com: import("@robot-model").Vec3 | null }>(`/api/projects/${project}/com`),
};
