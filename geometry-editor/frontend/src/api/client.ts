const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json();
}

export const api = {
  health: () => req<{ status: string }>("/api/health"),
  listProjects: () => req<{ projects: string[]; active: string | null }>("/api/projects"),
  createProject: (name: string) =>
    req<{ project: string; model: import("@robot-model").RobotModel }>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  loadProject: (name: string) =>
    req<{ project: string; model: import("@robot-model").RobotModel }>(`/api/projects/${name}/load`, {
      method: "POST",
    }),
  getModel: (name: string) => req<import("@robot-model").RobotModel>(`/api/projects/${name}/model`),
  addChildLink: (
    project: string,
    parentId: string,
    body: { name: string; joint_name: string; joint_type?: string }
  ) =>
    req(`/api/projects/${project}/links/${parentId}/child`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  removeLink: (project: string, linkId: string) =>
    req(`/api/projects/${project}/links/${linkId}`, { method: "DELETE" }),
  renameLink: (project: string, linkId: string, name: string) =>
    req(`/api/projects/${project}/links/${linkId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  updateLinkFrame: (project: string, linkId: string, frame: unknown) =>
    req(`/api/projects/${project}/links/${linkId}/frame`, {
      method: "PUT",
      body: JSON.stringify(frame),
    }),
  removeJoint: (project: string, jointId: string) =>
    req(`/api/projects/${project}/joints/${jointId}`, { method: "DELETE" }),
  renameJoint: (project: string, jointId: string, name: string) =>
    req(`/api/projects/${project}/joints/${jointId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  updateJoint: (project: string, jointId: string, data: Record<string, unknown>) =>
    req(`/api/projects/${project}/joints/${jointId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  addShape: (project: string, linkId: string, shape_type: string) =>
    req(`/api/projects/${project}/links/${linkId}/shapes`, {
      method: "POST",
      body: JSON.stringify({ shape_type }),
    }),
  removeShape: (project: string, linkId: string, shapeId: string) =>
    req(`/api/projects/${project}/links/${linkId}/shapes/${shapeId}`, { method: "DELETE" }),
  updateShapeType: (project: string, linkId: string, shapeId: string, shape_type: string) =>
    req(`/api/projects/${project}/links/${linkId}/shapes/${shapeId}/type`, {
      method: "PUT",
      body: JSON.stringify({ shape_type }),
    }),
  updateDimensions: (project: string, linkId: string, shapeId: string, dimensions: number[]) =>
    req(`/api/projects/${project}/links/${linkId}/shapes/${shapeId}/dimensions`, {
      method: "PUT",
      body: JSON.stringify({ dimensions }),
    }),
  updateTransform: (
    project: string,
    linkId: string,
    shapeId: string,
    position: unknown,
    rotation: unknown
  ) =>
    req(`/api/projects/${project}/links/${linkId}/shapes/${shapeId}/transform`, {
      method: "PUT",
      body: JSON.stringify({ position, rotation }),
    }),
  mirror: (project: string, source_prefix: string, target_prefix: string) =>
    req<import("@robot-model").RobotModel>(`/api/projects/${project}/mirror`, {
      method: "POST",
      body: JSON.stringify({ source_prefix, target_prefix }),
    }),
  copy: (project: string, source_prefix: string, target_prefix: string) =>
    req<import("@robot-model").RobotModel>(`/api/projects/${project}/copy`, {
      method: "POST",
      body: JSON.stringify({ source_prefix, target_prefix }),
    }),
  listTemplates: () => req<{ templates: import("@robot-model").TemplateInfo[] }>("/api/templates"),
  insertTemplate: (project: string, template_id: string) =>
    req<import("@robot-model").RobotModel>(`/api/projects/${project}/templates`, {
      method: "POST",
      body: JSON.stringify({ template_id }),
    }),
  setNamingConvention: (project: string, convention: string) =>
    req<import("@robot-model").RobotModel>(`/api/projects/${project}/naming-convention`, {
      method: "PUT",
      body: JSON.stringify({ convention }),
    }),
  validate: (project: string) =>
    req<{ task_id: string }>(`/api/projects/${project}/validate`, { method: "POST" }),
  exportUrdf: (project: string) =>
    req<{ task_id: string }>(`/api/projects/${project}/export/urdf`, { method: "POST" }),
  exportSdf: (project: string) =>
    req<{ task_id: string }>(`/api/projects/${project}/export/gazebo`, { method: "POST" }),
  exportBoth: (project: string) =>
    req<{ task_id: string }>(`/api/projects/${project}/export/both`, { method: "POST" }),
  getTask: (taskId: string) =>
    req<{ status: string; logs: { level: string; message: string }[]; result?: unknown }>(
      `/api/tasks/${taskId}`
    ),
  measureDistance: (project: string, link_a_id: string, link_b_id: string) =>
    req<import("@robot-model").MeasurementResult>(`/api/projects/${project}/measure/distance`, {
      method: "POST",
      body: JSON.stringify({ link_a_id, link_b_id }),
    }),
  measureHeight: (project: string, link_id: string) =>
    req<import("@robot-model").MeasurementResult>(`/api/projects/${project}/measure/height`, {
      method: "POST",
      body: JSON.stringify({ link_id }),
    }),
  measureLinkLength: (project: string, child_link_id: string) =>
    req<import("@robot-model").MeasurementResult>(`/api/projects/${project}/measure/link-length`, {
      method: "POST",
      body: JSON.stringify({ child_link_id }),
    }),
  measureAngle: (project: string, joint_a_id: string, joint_b_id: string) =>
    req<import("@robot-model").MeasurementResult>(`/api/projects/${project}/measure/angle`, {
      method: "POST",
      body: JSON.stringify({ joint_a_id, joint_b_id }),
    }),
  measureLegReach: (project: string, hip_link_id: string, foot_link_id: string) =>
    req<import("@robot-model").MeasurementResult>(`/api/projects/${project}/measure/leg-reach`, {
      method: "POST",
      body: JSON.stringify({ hip_link_id, foot_link_id }),
    }),
  createSnapshot: (project: string) =>
    req<{ snapshot_id: string }>(`/api/projects/${project}/snapshots`, { method: "POST" }),
  restoreSnapshot: (project: string, snapId: string) =>
    req<{ model: import("@robot-model").RobotModel }>(
      `/api/projects/${project}/snapshots/${snapId}/restore`,
      { method: "POST" }
    ),
  getDefaultPose: (project: string) =>
    req<{
      pose: import("@robot-model").Pose | null;
      default_pose_id: string | null;
      model: import("@robot-model").RobotModel;
    }>(`/api/projects/${project}/default-pose`),
  savePose: (project: string, poseId: string) =>
    req<import("@robot-model").Pose>(`/api/projects/${project}/poses/${poseId}/save`, { method: "POST" }),
  updatePoseJoint: (project: string, poseId: string, jointId: string, value: number) =>
    req<{ pose: import("@robot-model").Pose; model: import("@robot-model").RobotModel }>(
      `/api/projects/${project}/poses/${poseId}/joints/${jointId}`,
      { method: "PATCH", body: JSON.stringify({ value }) }
    ),
  resetDefaultPoseStand: (project: string) =>
    req<{ pose: import("@robot-model").Pose; model: import("@robot-model").RobotModel }>(
      `/api/projects/${project}/default-pose/reset-stand`,
      { method: "POST" }
    ),
};

export function wsLogsUrl(): string {
  const base = BASE.replace(/^http/, "ws");
  return `${base}/ws/logs`;
}
