import { useEffect, useRef, useState } from "react";
import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";

interface Props {
  projects: string[];
  newProjectName: string;
  setNewProjectName: (v: string) => void;
  onCreateProject: () => void;
  onLoadProject: (name: string) => void;
  onReloadModel: (name: string) => void;
}

export function MenuBar({
  projects,
  newProjectName,
  setNewProjectName,
  onCreateProject,
  onLoadProject,
  onReloadModel,
}: Props) {
  const project = useEditorStore((s) => s.project);
  const setModel = useEditorStore((s) => s.setModel);
  const setEditorMode = useEditorStore((s) => s.setEditorMode);
  const log = useEditorStore((s) => s.log);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [templates, setTemplates] = useState<
    { id: string; name: string; jointCount: number; category: string; description?: string }[]
  >([]);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listTemplates().then((r) => setTemplates(r.templates)).catch(() => {});
  }, []);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) setOpenMenu(null);
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const insertTemplate = async (id: string) => {
    if (!project) {
      log("Create or load a project first");
      return;
    }
    try {
      const m = await api.insertTemplate(project, id);
      setModel(m);
      const label = templates.find((t) => t.id === id)?.name ?? id;
      log(`Loaded template: ${label}`);
    } catch (e) {
      log(String(e));
    }
    setOpenMenu(null);
  };

  const robotTemplates = templates.filter((t) => t.category === "robot");
  const partTemplates = templates.filter((t) => t.category !== "robot");

  const toggle = (menu: string) => (e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenu(openMenu === menu ? null : menu);
  };

  return (
    <div className="menu-bar" ref={barRef}>
      <span className="menu-brand">QuadRL</span>

      <div className="menu-item">
        <button type="button" className="menu-btn" onClick={toggle("file")}>
          File
        </button>
        {openMenu === "file" && (
          <div className="menu-dropdown">
            <div className="menu-section">
              <label className="menu-label">New project name</label>
              <input value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} />
              <button type="button" onClick={() => { onCreateProject(); setOpenMenu(null); }}>
                New Project
              </button>
            </div>
            <hr />
            <label className="menu-label">Open project</label>
            <select
              value={project ?? ""}
              onChange={(e) => {
                if (e.target.value) onLoadProject(e.target.value);
                setOpenMenu(null);
              }}
            >
              <option value="">— select —</option>
              {projects.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="menu-item">
        <button type="button" className="menu-btn" onClick={toggle("templates")}>
          Templates
        </button>
        {openMenu === "templates" && (
          <div className="menu-dropdown menu-dropdown-wide">
            <div className="menu-group-title">Robots</div>
            {robotTemplates.map((t) => (
              <button key={t.id} type="button" className="menu-entry" onClick={() => insertTemplate(t.id)}>
                <span>{t.name}</span>
                <span className="menu-entry-meta">{t.jointCount} DOF</span>
              </button>
            ))}
            <div className="menu-group-title">Parts &amp; Limbs</div>
            {partTemplates.map((t) => (
              <button key={t.id} type="button" className="menu-entry" onClick={() => insertTemplate(t.id)}>
                <span>{t.name}</span>
                <span className="menu-entry-meta">{t.category}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="menu-item">
        <button type="button" className="menu-btn" onClick={toggle("tools")}>
          Tools
        </button>
        {openMenu === "tools" && project && (
          <div className="menu-dropdown">
            <button
              type="button"
              onClick={() => {
                setEditorMode("pose");
                setOpenMenu(null);
              }}
            >
              Default Pose editor…
            </button>
            <hr />
            <label className="menu-label">Naming convention</label>
            <select
              value={useEditorStore.getState().model?.namingConvention ?? "LOWER"}
              onChange={async (e) => {
                await api.setNamingConvention(project, e.target.value);
                onReloadModel(project);
              }}
            >
              <option value="LOWER">fl_hip_joint</option>
              <option value="ROS2_UPPER">FL_hip_joint</option>
            </select>
            <button type="button" onClick={async () => {
              await api.mirror(project, "fl", "fr");
              onReloadModel(project);
              setOpenMenu(null);
            }}>Mirror fl → fr</button>
            <button type="button" onClick={async () => {
              await api.copy(project, "fl", "fr");
              onReloadModel(project);
              setOpenMenu(null);
            }}>Copy fl → fr</button>
          </div>
        )}
      </div>
    </div>
  );
}
