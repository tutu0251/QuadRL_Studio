import * as THREE from "three";

/** Symmetric 3x3 inertia tensor → principal values and axis directions (columns). */
export function principalInertia(
  ixx: number,
  ixy: number,
  ixz: number,
  iyy: number,
  iyz: number,
  izz: number
): { values: [number, number, number]; axes: THREE.Vector3[] } {
  const arr = [ixx, ixy, ixz, ixy, iyy, iyz, ixz, iyz, izz];
  const { values, vectors } = symmetricEigen3(arr);
  const axes = [
    new THREE.Vector3(vectors[0], vectors[1], vectors[2]),
    new THREE.Vector3(vectors[3], vectors[4], vectors[5]),
    new THREE.Vector3(vectors[6], vectors[7], vectors[8]),
  ];
  return { values, axes };
}

function symmetricEigen3(a: number[]): { values: [number, number, number]; vectors: number[] } {
  // Jacobi iteration for 3x3 symmetric
  let m = a.slice();
  let v = [1, 0, 0, 0, 1, 0, 0, 0, 1];
  for (let iter = 0; iter < 24; iter++) {
    let p = 0,
      q = 1;
    let max = Math.abs(m[1]);
    if (Math.abs(m[2]) > max) {
      max = Math.abs(m[2]);
      p = 0;
      q = 2;
    }
    if (Math.abs(m[5]) > max) {
      p = 1;
      q = 2;
    }
    if (max < 1e-12) break;
    const theta = 0.5 * Math.atan2(2 * m[p + q * 3], m[q + q * 3] - m[p + p * 3]);
    const c = Math.cos(theta),
      s = Math.sin(theta);
    const app = c * c * m[p + p * 3] + s * s * m[q + q * 3] + 2 * s * c * m[p + q * 3];
    const aqq = s * s * m[p + p * 3] + c * c * m[q + q * 3] - 2 * s * c * m[p + q * 3];
    m[p + p * 3] = app;
    m[q + q * 3] = aqq;
    m[p + q * 3] = m[q + p * 3] = 0;
    const rip = [0, 1, 2].filter((i) => i !== p && i !== q);
    for (const r of rip) {
      const mrp = m[r + p * 3],
        mrq = m[r + q * 3];
      m[r + p * 3] = c * mrp - s * mrq;
      m[p + r * 3] = m[r + p * 3];
      m[r + q * 3] = s * mrp + c * mrq;
      m[q + r * 3] = m[r + q * 3];
    }
    for (let r = 0; r < 3; r++) {
      const vr = v[r + p * 3],
        vq = v[r + q * 3];
      v[r + p * 3] = c * vr - s * vq;
      v[r + q * 3] = s * vr + c * vq;
    }
  }
  const values: [number, number, number] = [m[0], m[4], m[8]];
  return { values, vectors: v };
}
