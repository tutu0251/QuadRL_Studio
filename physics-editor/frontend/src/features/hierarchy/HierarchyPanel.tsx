import { useMemo, useState, type ReactNode } from "react";
import type { Link, RobotModel } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";

function LinkNode({ link, model, depth }: { link: Link; model: RobotModel; depth: number }) {
  const selection = useEditorStore((s) => s.selection);
  const setSelection = useEditorStore((s) => s.setSelection);
  const [collapsed, setCollapsed] = useState(false);
  const sel = selection?.kind === "link" && selection.id === link.id;
  const children = model.joints.filter((j) => j.parentLinkId === link.id);
  const hasChildren = children.length > 0;

  return (
    <div>
      <div
        className={`hierarchy-row ${sel ? "selected" : ""}`}
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="expand-btn"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand" : "Collapse"}
          >
            {collapsed ? "▶" : "▼"}
          </button>
        ) : (
          <span className="expand-btn placeholder" />
        )}
        <button
          type="button"
          className="hierarchy-item"
          onClick={() => setSelection({ kind: "link", id: link.id })}
        >
          <span className={`hierarchy-icon ${link.isFoot ? "foot" : ""}`}>
            {link.isFoot ? "⬤" : "◆"}
          </span>
          <span className="hierarchy-name">{link.name}</span>
          <span className="tree-meta">{link.inertial.mass.toFixed(2)} kg</span>
        </button>
      </div>
      {!collapsed &&
        children.map((j) => {
          const child = model.links.find((l) => l.id === j.childLinkId);
          return child ? <LinkNode key={child.id} link={child} model={model} depth={depth + 1} /> : null;
        })}
    </div>
  );
}

export function HierarchyPanel() {
  const model = useEditorStore((s) => s.model);
  const [filter, setFilter] = useState("");

  const childIds = useMemo(
    () => (model ? new Set(model.joints.map((j) => j.childLinkId)) : new Set<string>()),
    [model]
  );
  const roots = useMemo(
    () => model?.links.filter((l) => !childIds.has(l.id)) ?? [],
    [model, childIds]
  );

  const totalMass = model?.links.reduce((s, l) => s + l.inertial.mass, 0) ?? 0;
  const footCount = model?.links.filter((l) => l.isFoot).length ?? 0;

  const filterLower = filter.toLowerCase();
  const renderFiltered = (link: Link, depth: number): ReactNode => {
    const match = !filterLower || link.name.toLowerCase().includes(filterLower);
    const childJoints = model!.joints.filter((j) => j.parentLinkId === link.id);
    const childNodes = childJoints.flatMap((j) => {
      const c = model!.links.find((l) => l.id === j.childLinkId);
      return c ? [renderFiltered(c, depth + 1)] : [];
    });
    if (!match && !childNodes.some(Boolean)) return null;
    if (!match) return <>{childNodes}</>;
    return <LinkNode key={link.id} link={link} model={model!} depth={depth} />;
  };

  if (!model) {
    return (
      <div className="unity-panel hierarchy-panel">
        <div className="panel-header">Hierarchy</div>
        <div className="panel-empty-state">
          <p className="empty-title">No robot loaded</p>
          <p className="empty-desc">File → select a project → Import geo URDF</p>
        </div>
      </div>
    );
  }

  return (
    <div className="unity-panel hierarchy-panel">
      <div className="panel-header">
        <span>Hierarchy</span>
        <span className="panel-header-meta">{model.links.length} links</span>
      </div>
      <div className="hierarchy-summary">
        <span>{totalMass.toFixed(2)} kg total</span>
        <span>{footCount} feet</span>
      </div>
      <div className="hierarchy-search">
        <input
          type="search"
          placeholder="Filter links…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <div className="hierarchy-tree">
        <div className="hierarchy-row robot-root">
          <span className="hierarchy-icon">🤖</span>
          <span className="robot-name">{model.name}</span>
        </div>
        {filter
          ? roots.map((r) => renderFiltered(r, 0))
          : roots.map((r) => <LinkNode key={r.id} link={r} model={model} depth={0} />)}
      </div>
    </div>
  );
}
