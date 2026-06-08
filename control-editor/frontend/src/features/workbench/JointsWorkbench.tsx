import { Fragment, useMemo, useState } from "react";
import type { JointControlConfig } from "@control-model";
import { PROFILE_IMPLEMENTED, PROFILE_LABELS } from "@control-model";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

const LEG_LABELS: Record<string, string> = {
  FL: "Front-left", LF: "Front-left",
  FR: "Front-right", RF: "Front-right",
  RL: "Rear-left", HL: "Rear-left", LH: "Rear-left",
  RR: "Rear-right", HR: "Rear-right", RH: "Rear-right",
};

function groupKey(name: string): string | null {
  const i = name.search(/[_-]/);
  return i > 0 ? name.slice(0, i).toUpperCase() : null;
}

function groupLabel(key: string): string {
  return LEG_LABELS[key] ?? key;
}

/** A compact inline-editable numeric cell. */
function NumCell({
  value,
  step,
  min,
  disabled,
  onCommit,
}: {
  value: number;
  step: number;
  min?: number;
  disabled?: boolean;
  onCommit: (v: number) => void;
}) {
  return (
    <td className="num-cell">
      <input
        type="number"
        step={step}
        min={min}
        disabled={disabled}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onCommit(parseFloat(e.target.value) || 0)}
      />
    </td>
  );
}

export function JointsWorkbench() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setModel = useEditorStore((s) => s.setModel);
  const setSelection = useEditorStore((s) => s.setSelection);
  const log = useEditorStore((s) => s.log);
  const [filter, setFilter] = useState("");

  const patch = async (jointName: string, body: Record<string, number | boolean>) => {
    if (!project) return;
    try {
      setModel(await api.updateJoint(project, jointName, body));
    } catch (e) {
      log(String(e));
    }
  };

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const joints = model?.actuatedJoints ?? [];
    return q ? joints.filter((j) => j.name.toLowerCase().includes(q)) : joints;
  }, [model, filter]);

  // Group rows by detected leg prefix; fall back to a single flat group.
  const groups = useMemo(() => {
    const map = new Map<string, JointControlConfig[]>();
    for (const j of filtered) {
      const k = groupKey(j.name) ?? "";
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(j);
    }
    const entries = [...map.entries()];
    const grouped = entries.length > 1 && entries.every(([k]) => k !== "");
    return { grouped, entries };
  }, [filtered]);

  if (!model) {
    return (
      <section className="panel workbench-panel">
        <header className="panel-header">
          <div>
            <h2>Joints</h2>
            <p className="panel-subtitle">No control model — File → select project → Import phy URDF.</p>
          </div>
        </header>
      </section>
    );
  }

  if (!PROFILE_IMPLEMENTED[model.trainingProfile]) {
    return (
      <section className="panel workbench-panel">
        <header className="panel-header">
          <h2>Joints</h2>
        </header>
        <div className="panel-empty-state">
          <p className="empty-title">{model.trainingProfile}</p>
          <p className="empty-desc">{PROFILE_LABELS[model.trainingProfile]}</p>
          <p className="empty-desc">Switch to ProfileA to edit position-control gains.</p>
        </div>
      </section>
    );
  }

  const colCount = 11;

  const renderRow = (j: JointControlConfig) => {
    const sel = selection?.kind === "joint" && selection.name === j.name;
    const cont = j.type === "continuous";
    return (
      <tr key={j.name} className={`joint-row ${sel ? "selected" : ""} ${j.enabled ? "" : "row-disabled"}`}>
        <td className="check-cell">
          <input
            type="checkbox"
            checked={j.enabled}
            onChange={(e) => void patch(j.name, { enabled: e.target.checked })}
            title={j.enabled ? "Enabled" : "Disabled"}
          />
        </td>
        <td className="joint-name-cell">
          <button
            type="button"
            className="joint-name-btn"
            onClick={() => setSelection({ kind: "joint", name: j.name })}
            title={j.childLinkName}
          >
            {j.name}
          </button>
        </td>
        <td className="joint-type-cell">{j.type}</td>
        <NumCell value={j.kp} step={1} min={0} onCommit={(v) => void patch(j.name, { kp: v })} />
        <NumCell value={j.kd} step={0.1} min={0} onCommit={(v) => void patch(j.name, { kd: v })} />
        <NumCell value={j.defaultPosition} step={0.01} onCommit={(v) => void patch(j.name, { defaultPosition: v })} />
        <NumCell value={j.actionScale} step={0.01} min={0} onCommit={(v) => void patch(j.name, { actionScale: v })} />
        <NumCell value={j.effort} step={1} min={0} onCommit={(v) => void patch(j.name, { effort: v })} />
        <NumCell value={j.velocity} step={0.1} min={0} onCommit={(v) => void patch(j.name, { velocity: v })} />
        {cont ? (
          <td className="num-cell muted">—</td>
        ) : (
          <NumCell value={j.lowerLimit} step={0.01} onCommit={(v) => void patch(j.name, { lowerLimit: v })} />
        )}
        {cont ? (
          <td className="num-cell muted">—</td>
        ) : (
          <NumCell value={j.upperLimit} step={0.01} onCommit={(v) => void patch(j.name, { upperLimit: v })} />
        )}
      </tr>
    );
  };

  return (
    <section className="panel workbench-panel">
      <header className="panel-header">
        <div>
          <h2>Joints</h2>
          <p className="panel-subtitle">Tune position-control gains inline — changes save on edit.</p>
        </div>
        <input
          className="workbench-search"
          type="search"
          placeholder="Filter joints…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </header>

      <div className="workbench-scroll">
        <table className="data-table workbench-table">
          <thead>
            <tr>
              <th className="check-cell" />
              <th>Joint</th>
              <th>Type</th>
              <th>Kp</th>
              <th>Kd</th>
              <th>Default</th>
              <th>Action&nbsp;scale</th>
              <th>Effort</th>
              <th>Velocity</th>
              <th>Lower</th>
              <th>Upper</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td className="muted" colSpan={colCount}>
                  No joints match “{filter}”.
                </td>
              </tr>
            )}
            {groups.grouped
              ? groups.entries.map(([key, joints]) => (
                  <Fragment key={`g-${key}`}>
                    <tr className="group-row">
                      <td colSpan={colCount}>
                        <span className="group-label">{groupLabel(key)}</span>
                        <span className="group-count">{joints.length}</span>
                      </td>
                    </tr>
                    {joints.map(renderRow)}
                  </Fragment>
                ))
              : filtered.map(renderRow)}
          </tbody>
        </table>
      </div>
    </section>
  );
}
