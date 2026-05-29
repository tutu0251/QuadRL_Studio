import type { Quat } from "@robot-model";

const RAD2DEG = 180 / Math.PI;
const DEG2RAD = Math.PI / 180;

/** Quaternion to roll-pitch-yaw in degrees (XYZ intrinsic, URDF convention). */
export function quatToEulerDeg(q: Quat): { x: number; y: number; z: number } {
  const x = q.x;
  const y = q.y;
  const z = q.z;
  const w = q.w;

  const sinr = 2 * (w * x + y * z);
  const cosr = 1 - 2 * (x * x + y * y);
  const roll = Math.atan2(sinr, cosr);

  const sinp = 2 * (w * y - z * x);
  const pitch = Math.abs(sinp) >= 1 ? Math.sign(sinp) * (Math.PI / 2) : Math.asin(sinp);

  const siny = 2 * (w * z + x * y);
  const cosy = 1 - 2 * (y * y + z * z);
  const yaw = Math.atan2(siny, cosy);

  return { x: roll * RAD2DEG, y: pitch * RAD2DEG, z: yaw * RAD2DEG };
}

/** Euler degrees to quaternion (XYZ intrinsic). */
export function eulerDegToQuat(euler: { x: number; y: number; z: number }): Quat {
  const roll = euler.x * DEG2RAD;
  const pitch = euler.y * DEG2RAD;
  const yaw = euler.z * DEG2RAD;

  const cr = Math.cos(roll / 2);
  const sr = Math.sin(roll / 2);
  const cp = Math.cos(pitch / 2);
  const sp = Math.sin(pitch / 2);
  const cy = Math.cos(yaw / 2);
  const sy = Math.sin(yaw / 2);

  return {
    x: sr * cp * cy - cr * sp * sy,
    y: cr * sp * cy + sr * cp * sy,
    z: cr * cp * sy - sr * sp * cy,
    w: cr * cp * cy + sr * sp * sy,
  };
}
