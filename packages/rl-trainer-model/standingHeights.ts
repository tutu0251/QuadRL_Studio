/** Shared spawn / command / termination height policy (base_link world Z). */

export const HEIGHT_REFERENCE = "base_link_origin_z" as const;

/** Allowed drop below nominal stand before fall termination (m). */
export const FALL_DROP_MARGIN_M = 0.1;

export interface StandingHeightParams {
  reference: typeof HEIGHT_REFERENCE;
  spawnZ: number;
  targetBodyHeight: number;
  fallBaseHeightThreshold: number;
  fallDropMarginM: number;
}

export interface HeightPolicyYaml {
  reference: string;
  spawn_z: number;
  target_body_height: number;
  fall_base_height_threshold: number;
  fall_drop_margin_m: number;
}

/** Derive aligned heights from grounded spawn Z (feet on z=0). */
export function standingHeightParams(
  groundedSpawnZ: number,
  fallDropMarginM: number = FALL_DROP_MARGIN_M
): StandingHeightParams {
  const spawnZ = round4(groundedSpawnZ);
  const targetBodyHeight = spawnZ;
  const fallBaseHeightThreshold = round4(targetBodyHeight - fallDropMarginM);
  return {
    reference: HEIGHT_REFERENCE,
    spawnZ,
    targetBodyHeight,
    fallBaseHeightThreshold,
    fallDropMarginM,
  };
}

export function heightPolicyToYaml(h: StandingHeightParams): HeightPolicyYaml {
  return {
    reference: h.reference,
    spawn_z: h.spawnZ,
    target_body_height: h.targetBodyHeight,
    fall_base_height_threshold: h.fallBaseHeightThreshold,
    fall_drop_margin_m: h.fallDropMarginM,
  };
}

export function assertHeightPolicyConsistent(h: StandingHeightParams): void {
  if (h.targetBodyHeight !== h.spawnZ) {
    throw new Error(
      `targetBodyHeight (${h.targetBodyHeight}) must equal spawnZ (${h.spawnZ})`
    );
  }
  if (h.fallBaseHeightThreshold >= h.targetBodyHeight) {
    throw new Error(
      `fallBaseHeightThreshold (${h.fallBaseHeightThreshold}) must be below targetBodyHeight (${h.targetBodyHeight})`
    );
  }
  const expectedFall = round4(h.targetBodyHeight - h.fallDropMarginM);
  if (h.fallBaseHeightThreshold !== expectedFall) {
    throw new Error(
      `fallBaseHeightThreshold (${h.fallBaseHeightThreshold}) expected ${expectedFall}`
    );
  }
}

/** Editor / template placeholder until geo spawn export is synced. */
export const PLACEHOLDER_BODY_HEIGHT_M = 0.35;

export function fallThresholdForTarget(
  targetBodyHeight: number,
  fallDropMarginM: number = FALL_DROP_MARGIN_M
): number {
  return round4(targetBodyHeight - fallDropMarginM);
}

function round4(v: number): number {
  return Math.round(v * 10000) / 10000;
}
