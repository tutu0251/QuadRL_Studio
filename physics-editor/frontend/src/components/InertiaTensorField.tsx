import type { Inertial } from "@robot-model";

type InertiaKey = "ixx" | "ixy" | "ixz" | "iyy" | "iyz" | "izz";

const CELLS: { key: InertiaKey; row: number; col: number }[] = [
  { key: "ixx", row: 1, col: 1 },
  { key: "ixy", row: 1, col: 2 },
  { key: "ixz", row: 1, col: 3 },
  { key: "iyy", row: 2, col: 2 },
  { key: "iyz", row: 2, col: 3 },
  { key: "izz", row: 3, col: 3 },
];

const LABELS: Record<InertiaKey, string> = {
  ixx: "ixx",
  ixy: "ixy",
  ixz: "ixz",
  iyy: "iyy",
  iyz: "iyz",
  izz: "izz",
};

export function InertiaTensorField({
  value,
  onChange,
}: {
  value: Pick<Inertial, InertiaKey>;
  onChange: (v: Pick<Inertial, InertiaKey>) => void;
}) {
  return (
    <div className="inertia-matrix-block">
      <div className="inertia-matrix-header">
        <span className="inertia-matrix-title">Inertia tensor</span>
        <span className="inertia-matrix-unit">kg·m² · link frame</span>
      </div>

      <div className="inertia-matrix-grid" role="grid" aria-label="Symmetric inertia tensor">
        {CELLS.map(({ key, row, col }) => (
          <label
            key={key}
            className="inertia-cell"
            style={{ gridRow: row, gridColumn: col }}
          >
            <span className="inertia-cell-label">{LABELS[key]}</span>
            <input
              type="number"
              step={0.0001}
              value={value[key]}
              onChange={(e) => onChange({ ...value, [key]: parseFloat(e.target.value) || 0 })}
              aria-label={LABELS[key]}
            />
          </label>
        ))}
      </div>

      <p className="inertia-matrix-hint">Symmetric · ixy = iyx, ixz = izx, iyz = izy</p>
    </div>
  );
}
