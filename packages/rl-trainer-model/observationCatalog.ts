/** Procedural observation groups assembled in the RL env (not separate ROS sensors). */

export type ObservationSource = "procedural" | "sensor";

export interface ObservationNormDefaults {
  scale: number;
  offset: number;
  clipMin: number | null;
  clipMax: number | null;
}

export interface ObservationCatalogEntry {
  id: string;
  label: string;
  kind: string;
  category: "state" | "command" | "sensor";
  description: string;
  dimsHint?: string;
}

export const PROCEDURAL_OBSERVATION_CATALOG: ObservationCatalogEntry[] = [
  {
    id: "joint_positions",
    label: "Joint positions",
    kind: "joint_state",
    category: "state",
    description: "Relative joint positions from the sim / ros2_control state.",
    dimsHint: "n_joints",
  },
  {
    id: "joint_velocities",
    label: "Joint velocities",
    kind: "joint_state",
    category: "state",
    description: "Joint velocities from the sim / ros2_control state.",
    dimsHint: "n_joints",
  },
  {
    id: "last_actions",
    label: "Last actions",
    kind: "action",
    category: "state",
    description: "Previous policy action vector (action history for smoothness).",
    dimsHint: "n_actions",
  },
  {
    id: "commands",
    label: "Commands",
    kind: "command",
    category: "command",
    description: "Target velocity, height, and gait command from the task.",
    dimsHint: "4–5",
  },
  {
    id: "base_lin_vel",
    label: "Base linear velocity",
    kind: "base_state",
    category: "state",
    description: "Base linear velocity in body frame (odom or kinematics).",
    dimsHint: "3",
  },
  {
    id: "base_ang_vel",
    label: "Base angular velocity",
    kind: "base_state",
    category: "state",
    description: "Base angular velocity (IMU or kinematics).",
    dimsHint: "3",
  },
  {
    id: "projected_gravity",
    label: "Projected gravity",
    kind: "orientation",
    category: "state",
    description: "Gravity vector in body frame (IMU orientation or equivalent).",
    dimsHint: "3",
  },
];

export const OBSERVATION_CATEGORY_HINTS: Record<string, string> = {
  state: "Procedural state from sim / controller feedback",
  command: "Task command reference included in the observation vector",
  sensor: "ROS topic bridged from Gazebo (see sens_*_observations.yaml)",
};

export const OBSERVATION_KIND_HINTS: Record<string, string> = {
  joint_state: "Requires ros2_control joint state interface",
  action: "Uses previous policy output from the env wrapper",
  command: "Uses stage command targets from RL config",
  base_state: "Uses odometry or differentiated base pose",
  orientation: "Uses IMU orientation or projected gravity",
  imu: "sensor_msgs/Imu — angular velocity, acceleration, optional orientation",
  contact: "Foot contact / slip from Gazebo contact sensors",
  odom: "Base velocity from odometry source",
  lidar: "Range scan (usually disabled for locomotion PPO)",
};

const catalogById = new Map(PROCEDURAL_OBSERVATION_CATALOG.map((e) => [e.id, e]));

export const PROCEDURAL_NORM: Record<string, ObservationNormDefaults> = {
  joint_positions: { scale: 2, offset: 0, clipMin: -1, clipMax: 1 },
  joint_velocities: { scale: 6, offset: 0, clipMin: -1, clipMax: 1 },
  last_actions: { scale: 1, offset: 0, clipMin: -1, clipMax: 1 },
  commands: { scale: 1, offset: 0, clipMin: -1, clipMax: 1 },
  base_lin_vel: { scale: 2, offset: 0, clipMin: -1, clipMax: 1 },
  base_ang_vel: { scale: 8, offset: 0, clipMin: -1, clipMax: 1 },
  projected_gravity: { scale: 1, offset: 0, clipMin: null, clipMax: null },
};

export const SENSOR_KIND_NORM: Record<string, ObservationNormDefaults> = {
  imu: { scale: 5, offset: 0, clipMin: -1, clipMax: 1 },
  contact: { scale: 1, offset: 0, clipMin: 0, clipMax: 1 },
  odom: { scale: 2, offset: 0, clipMin: -1, clipMax: 1 },
  lidar: { scale: 30, offset: 0, clipMin: 0, clipMax: 1 },
};

export const OBSERVATION_NORM_FORMULA =
  "Env applies: clip((raw − offset) / scale, clipMin, clipMax). Omit clip when min/max are empty.";

export const OBSERVATION_NORM_HINTS: Record<string, string> = {
  scale: "Divisor — typical magnitude of raw values (e.g. 2 for joint rad, 6 for rad/s).",
  offset: "Subtract from raw value before scaling (usually 0).",
  clipMin: "Lower clip after scaling; leave empty for no lower bound.",
  clipMax: "Upper clip after scaling; leave empty for no upper bound.",
};

export function getRecommendedObservationNorm(term: {
  id: string;
  source: ObservationSource;
  kind: string;
}): ObservationNormDefaults {
  if (term.source === "procedural" && term.id in PROCEDURAL_NORM) {
    return { ...PROCEDURAL_NORM[term.id] };
  }
  const kind = term.kind.toLowerCase();
  if (kind in SENSOR_KIND_NORM) {
    return { ...SENSOR_KIND_NORM[kind] };
  }
  return { scale: 1, offset: 0, clipMin: -1, clipMax: 1 };
}

export function getProceduralObservationEntry(id: string): ObservationCatalogEntry | undefined {
  return catalogById.get(id);
}
