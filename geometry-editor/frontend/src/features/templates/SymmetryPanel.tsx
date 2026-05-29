import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";

export function SymmetryPanel() {
  const project = useEditorStore((s) => s.project);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);

  const run = async (action: "mirror" | "copy", src: string, tgt: string) => {
    if (!project) return;
    try {
      const m =
        action === "mirror"
          ? await api.mirror(project, src, tgt)
          : await api.copy(project, src, tgt);
      setModel(m);
      log(`${action} ${src} → ${tgt}`);
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <section>
      <h2>Symmetry</h2>
      <div className="btn-row">
        <button type="button" onClick={() => run("mirror", "fl", "fr")}>
          Mirror fl→fr
        </button>
        <button type="button" onClick={() => run("mirror", "fl", "rl")}>
          Mirror fl→rl
        </button>
        <button type="button" onClick={() => run("copy", "fl", "fr")}>
          Copy fl→fr
        </button>
      </div>
    </section>
  );
}
