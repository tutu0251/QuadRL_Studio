import type { Link, RobotModel } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";

function buildTree(model: RobotModel): Link[] {
  const childIds = new Set(model.joints.map((j) => j.childLinkId));
  return model.links.filter((l) => !childIds.has(l.id));
}

function TreeBranch({ model, link, depth }: { model: RobotModel; link: Link; depth: number }) {
  const selection = useEditorStore((s) => s.selection);
  const setSelection = useEditorStore((s) => s.setSelection);
  const linkMap = new Map(model.links.map((l) => [l.id, l]));

  const selLink = selection?.kind === "link" && selection.id === link.id;
  const outgoing = model.joints.filter((j) => j.parentLinkId === link.id);

  return (
    <div className="tree-node" style={{ paddingLeft: depth * 12 }}>
      <button
        type="button"
        className={`tree-btn ${selLink ? "active" : ""}`}
        onClick={() => setSelection({ kind: "link", id: link.id })}
      >
        🔗 {link.name}
      </button>
      {outgoing.map((joint) => {
        const child = linkMap.get(joint.childLinkId);
        if (!child) return null;
        const selJoint = selection?.kind === "joint" && selection.id === joint.id;
        return (
          <div key={joint.id} className="tree-joint-branch">
            <button
              type="button"
              className={`tree-btn joint ${selJoint ? "active" : ""}`}
              style={{ paddingLeft: (depth + 1) * 12 }}
              onClick={() => setSelection({ kind: "joint", id: joint.id })}
            >
              ⚙ {joint.name} ({joint.type})
            </button>
            <TreeBranch model={model} link={child} depth={depth + 2} />
          </div>
        );
      })}
    </div>
  );
}

interface Props {
  onAddChild: (parentLinkId: string) => void;
  onDeleteLink: (linkId: string) => void;
}

export function RobotTreeEditor({ onAddChild, onDeleteLink }: Props) {
  const model = useEditorStore((s) => s.model);
  const selection = useEditorStore((s) => s.selection);

  if (!model) return <p className="muted">No model loaded</p>;

  const tree = buildTree(model);
  const selectedLinkId = selection?.kind === "link" ? selection.id : null;

  return (
    <div className="tree-editor">
      <div className="btn-row">
        <button
          type="button"
          disabled={!selectedLinkId}
          onClick={() => selectedLinkId && onAddChild(selectedLinkId)}
        >
          + Child link
        </button>
        <button
          type="button"
          disabled={!selectedLinkId}
          onClick={() => selectedLinkId && onDeleteLink(selectedLinkId)}
        >
          Delete
        </button>
      </div>
      {tree.map((root) => (
        <TreeBranch key={root.id} model={model} link={root} depth={0} />
      ))}
    </div>
  );
}
