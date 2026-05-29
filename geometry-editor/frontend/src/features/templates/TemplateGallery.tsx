import { useEffect, useState } from "react";
import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";

export function TemplateGallery() {
  const project = useEditorStore((s) => s.project);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);
  const [templates, setTemplates] = useState<
    { id: string; name: string; jointCount: number; category: string }[]
  >([]);

  useEffect(() => {
    api.listTemplates().then((r) => setTemplates(r.templates)).catch(() => {});
  }, []);

  const insert = async (id: string) => {
    if (!project) return;
    try {
      const m = await api.insertTemplate(project, id);
      setModel(m);
      log(`Inserted template: ${id}`);
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <section>
      <h2>Templates</h2>
      <select
        defaultValue=""
        onChange={(e) => {
          if (e.target.value) insert(e.target.value);
          e.target.value = "";
        }}
      >
        <option value="">Insert template…</option>
        {templates.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name} ({t.jointCount} joints)
          </option>
        ))}
      </select>
    </section>
  );
}
