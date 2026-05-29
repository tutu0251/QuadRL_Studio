import { useState } from "react";
import { useEditorStore } from "../../stores/editorStore";

export function HierarchyPanel() {
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setSelection = useEditorStore((s) => s.setSelection);
  const [filter, setFilter] = useState("");

  if (!model) {
    return (
      <div className="unity-panel hierarchy-panel">
        <div className="panel-header">Joints</div>
        <div className="panel-empty-state">
          <p className="empty-title">No control model</p>
          <p className="empty-desc">File → select project → Import phy URDF</p>
        </div>
      </div>
    );
  }

  const filterLower = filter.toLowerCase();
  const joints = model.actuatedJoints.filter(
    (j) => !filterLower || j.name.toLowerCase().includes(filterLower)
  );

  return (
    <div className="unity-panel hierarchy-panel">
      <div className="panel-header">
        <span>Actuated joints</span>
        <span className="panel-header-meta">{model.actuatedJoints.length}</span>
      </div>
      <div className="hierarchy-summary">
        <span>{model.trainingProfile}</span>
        <span>{model.robotName}</span>
      </div>
      <div className="hierarchy-search">
        <input
          type="search"
          placeholder="Filter joints…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <div className="hierarchy-tree">
        {joints.map((j) => {
          const sel = selection?.kind === "joint" && selection.name === j.name;
          return (
            <div key={j.name} className={`hierarchy-row ${sel ? "selected" : ""}`}>
              <button
                type="button"
                className="hierarchy-item"
                onClick={() => setSelection({ kind: "joint", name: j.name })}
              >
                <span className={`hierarchy-icon ${j.enabled ? "" : "disabled"}`}>◎</span>
                <span className="hierarchy-name">{j.name}</span>
                <span className="tree-meta">Kp={j.kp.toFixed(1)}</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
