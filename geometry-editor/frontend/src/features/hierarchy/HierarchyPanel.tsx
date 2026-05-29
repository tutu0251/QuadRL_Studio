import { useMemo, useState, type ReactNode } from "react";
import type { Joint, Link, RobotModel } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";

function linkIcon(link: Link) {
  if (link.shapes.some((s) => s.type === "sphere")) return "●";
  if (link.shapes.some((s) => s.type === "capsule")) return "⬮";
  return "▣";
}

interface Props {
  onAddChild: (parentLinkId: string) => void;
  onDeleteLink: (linkId: string) => void;
}

export function HierarchyPanel({ onAddChild, onDeleteLink }: Props) {
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);
  const setSelection = useEditorStore((s) => s.setSelection);
  const [filter, setFilter] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const childIds = useMemo(
    () => (model ? new Set(model.joints.map((j) => j.childLinkId)) : new Set<string>()),
    [model]
  );
  const roots = useMemo(
    () => model?.links.filter((l) => !childIds.has(l.id)) ?? [],
    [model, childIds]
  );

  if (!model) {
    return (
      <div className="unity-panel hierarchy-panel">
        <div className="panel-header">Hierarchy</div>
        <p className="panel-empty">No robot loaded</p>
      </div>
    );
  }

  const toggleCollapse = (id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const isSelected = (kind: string, id: string) => {
    if (!selection) return false;
    if (kind === "link") return selection.kind === "link" && selection.id === id;
    if (kind === "joint") return selection.kind === "joint" && selection.id === id;
    if (kind === "shape") return selection.kind === "shape" && selection.shapeId === id;
    return false;
  };

  const matchesFilter = (name: string) =>
    !filter || name.toLowerCase().includes(filter.toLowerCase());

  const renderLink = (link: Link, depth: number): ReactNode => {
    const linkId = link.id;
    const childJoints = model.joints.filter((j) => j.parentLinkId === linkId);
    const hasChildren = childJoints.length > 0 || link.shapes.length > 0;
    const isCollapsed = collapsed.has(linkId);

    if (filter && !matchesFilter(link.name) && !childJoints.some((j) => matchesFilter(j.name))) {
      return childJoints.flatMap((j) => {
        const child = model.links.find((l) => l.id === j.childLinkId);
        return child ? renderLink(child, depth) : null;
      });
    }

    return (
      <div key={linkId}>
        <div
          className={`hierarchy-row ${isSelected("link", linkId) ? "selected" : ""}`}
          style={{ paddingLeft: 8 + depth * 14 }}
        >
          <button
            type="button"
            className="expand-btn"
            onClick={() => hasChildren && toggleCollapse(linkId)}
          >
            {hasChildren ? (isCollapsed ? "▶" : "▼") : " "}
          </button>
          <button
            type="button"
            className="hierarchy-item"
            onClick={() => setSelection({ kind: "link", id: linkId })}
          >
            <span className="hierarchy-icon">{linkIcon(link)}</span>
            {link.name}
          </button>
        </div>

        {!isCollapsed &&
          link.shapes.map((s) => (
            <div
              key={s.id}
              className={`hierarchy-row shape-row ${isSelected("shape", s.id) ? "selected" : ""}`}
              style={{ paddingLeft: 8 + (depth + 1) * 14 }}
            >
              <span className="expand-btn"> </span>
              <button
                type="button"
                className="hierarchy-item"
                onClick={() => setSelection({ kind: "shape", linkId, shapeId: s.id })}
              >
                <span className="hierarchy-icon">◇</span>
                {s.type}
              </button>
            </div>
          ))}

        {!isCollapsed &&
          childJoints.map((joint) => {
            const childLink = model.links.find((l) => l.id === joint.childLinkId);
            if (!childLink) return null;
            return (
              <div key={joint.id}>
                <div
                  className={`hierarchy-row joint-row ${isSelected("joint", joint.id) ? "selected" : ""}`}
                  style={{ paddingLeft: 8 + (depth + 1) * 14 }}
                >
                  <span className="expand-btn"> </span>
                  <button
                    type="button"
                    className="hierarchy-item"
                    onClick={() => setSelection({ kind: "joint", id: joint.id })}
                  >
                    <span className="hierarchy-icon">⚙</span>
                    {joint.name}
                  </button>
                </div>
                {renderLink(childLink, depth + 2)}
              </div>
            );
          })}
      </div>
    );
  };

  const selectedLinkId = selection?.kind === "link" ? selection.id : null;

  return (
    <div className="unity-panel hierarchy-panel">
      <div className="panel-header">
        <span>Hierarchy</span>
        <div className="panel-header-actions">
          <button
            type="button"
            title="Add child link"
            disabled={!selectedLinkId}
            onClick={() => selectedLinkId && onAddChild(selectedLinkId)}
          >
            +
          </button>
          <button
            type="button"
            title="Delete selected"
            disabled={!selectedLinkId}
            onClick={() => selectedLinkId && onDeleteLink(selectedLinkId)}
          >
            −
          </button>
        </div>
      </div>
      <div className="hierarchy-search">
        <input
          type="search"
          placeholder="Search…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <div className="hierarchy-tree">
        <div className="hierarchy-row robot-root">
          <span className="expand-btn">▼</span>
          <span className="hierarchy-icon">🤖</span>
          <span className="robot-name">{model.name}</span>
        </div>
        {roots.map((r) => renderLink(r, 1))}
      </div>
    </div>
  );
}
