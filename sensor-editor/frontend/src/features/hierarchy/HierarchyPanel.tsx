import { useState } from "react";
import { SENSOR_KIND_LABELS } from "@sensor-model";
import { useEditorStore } from "../../stores/editorStore";

export function HierarchyPanel() {
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setSelection = useEditorStore((s) => s.setSelection);
  const [filter, setFilter] = useState("");
  const [tab, setTab] = useState<"sensors" | "links">("sensors");

  if (!model) {
    return (
      <div className="unity-panel hierarchy-panel">
        <div className="panel-header">Hierarchy</div>
        <div className="panel-empty-state">
          <p className="empty-title">No sensor model</p>
          <p className="empty-desc">File → select project → Import ctrl URDF</p>
        </div>
      </div>
    );
  }

  const filterLower = filter.toLowerCase();
  const sensors = model.sensors.filter(
    (s) =>
      !filterLower ||
      s.name.toLowerCase().includes(filterLower) ||
      s.parentLink.toLowerCase().includes(filterLower)
  );
  const links = model.linkNames.filter((l) => !filterLower || l.toLowerCase().includes(filterLower));

  return (
    <div className="unity-panel hierarchy-panel">
      <div className="panel-header">
        <span>Hierarchy</span>
        <span className="panel-header-meta">{model.sensors.length} sensors</span>
      </div>
      <div className="hierarchy-tabs">
        <button
          type="button"
          className={tab === "sensors" ? "tab active" : "tab"}
          onClick={() => setTab("sensors")}
        >
          Sensors
        </button>
        <button
          type="button"
          className={tab === "links" ? "tab active" : "tab"}
          onClick={() => setTab("links")}
        >
          Links ({model.linkNames.length})
        </button>
      </div>
      <div className="hierarchy-summary">
        <span>{model.robotName}</span>
        <span className="mono">{model.topicPrefix}</span>
      </div>
      <div className="hierarchy-search">
        <input
          type="search"
          placeholder="Filter…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <div className="hierarchy-tree">
        {tab === "links" &&
          links.map((l) => {
            const sel = selection?.kind === "link" && selection.name === l;
            return (
              <div key={l} className={`hierarchy-row ${sel ? "selected" : ""}`}>
                <button
                  type="button"
                  className="hierarchy-item"
                  onClick={() => setSelection({ kind: "link", name: l })}
                >
                  <span className="hierarchy-icon">▣</span>
                  <span className="hierarchy-name">{l}</span>
                </button>
              </div>
            );
          })}
        {tab === "sensors" &&
          sensors.map((s) => {
            const sel = selection?.kind === "sensor" && selection.id === s.id;
            return (
              <div key={s.id} className={`hierarchy-row ${sel ? "selected" : ""}`}>
                <button
                  type="button"
                  className="hierarchy-item"
                  onClick={() => setSelection({ kind: "sensor", id: s.id })}
                >
                  <span className={`hierarchy-icon ${s.enabled ? "" : "disabled"}`}>◎</span>
                  <span className="hierarchy-name">{s.name}</span>
                  <span className="tree-meta">{SENSOR_KIND_LABELS[s.kind]}</span>
                </button>
              </div>
            );
          })}
      </div>
    </div>
  );
}
