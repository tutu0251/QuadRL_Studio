import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import { useEditorStore } from "../../stores/editorStore";

type Props = {
  projects: string[];
  projectDetails: { name: string; hasGeoUrdf: boolean; hasPhysics: boolean }[];
  onLoadProject: (name: string) => void;
  onImport: () => void;
  onReload: () => void;
};

export function MenuBar({ projects, projectDetails, onLoadProject, onImport, onReload }: Props) {
  const project = useEditorStore((s) => s.project);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const barRef = useRef<HTMLDivElement>(null);

  const detail = projectDetails.find((d) => d.name === project);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) setOpenMenu(null);
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const toggle = (menu: string) => (e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenu(openMenu === menu ? null : menu);
  };

  return (
    <div className="menu-bar" ref={barRef}>
      <span className="menu-brand physics-brand">
        <span className="brand-mark" aria-hidden />
        Physics
      </span>

      <div className="menu-item">
        <button type="button" className="menu-btn" onClick={toggle("file")}>
          File
        </button>
        {openMenu === "file" && (
          <div className="menu-dropdown">
            <label className="menu-label">Project</label>
            <select
              className="menu-select full-width"
              value={project ?? ""}
              onChange={(e) => {
                if (e.target.value) onLoadProject(e.target.value);
                setOpenMenu(null);
              }}
            >
              <option value="">— select project —</option>
              {projects.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            {detail && (
              <div className="menu-status-chips">
                <span className={`chip ${detail.hasGeoUrdf ? "ok" : "warn"}`}>
                  {detail.hasGeoUrdf ? "geo URDF" : "no geo URDF"}
                </span>
                <span className={`chip ${detail.hasPhysics ? "ok" : ""}`}>
                  {detail.hasPhysics ? "physics saved" : "not imported"}
                </span>
              </div>
            )}
            <hr />
            <button
              type="button"
              className="menu-entry full-width"
              disabled={!project}
              onClick={() => {
                onImport();
                setOpenMenu(null);
              }}
            >
              Import geo URDF…
              <span className="menu-entry-meta">overwrite</span>
            </button>
            <button
              type="button"
              className="menu-entry full-width"
              disabled={!project}
              onClick={() => {
                onReload();
                setOpenMenu(null);
              }}
            >
              Reload model
            </button>
            <button
              type="button"
              className="menu-entry full-width"
              disabled={!project}
              onClick={() => {
                if (project) void api.estimateAll(project).then(onReload);
                setOpenMenu(null);
              }}
            >
              Auto-estimate all links
            </button>
          </div>
        )}
      </div>

      <div className="menu-item">
        <button type="button" className="menu-btn" onClick={toggle("view")}>
          View
        </button>
        {openMenu === "view" && (
          <div className="menu-dropdown">
            <ViewToggle label="Link COM markers" storeKey="showCom" />
            <ViewToggle label="Inertia principal axes" storeKey="showInertiaAxes" />
            <ViewToggle label="Whole-robot COM" storeKey="showWholeCom" />
          </div>
        )}
      </div>

      <span className="menu-spacer" />

      {project && (
        <span className="menu-context">
          {project}
          {detail && !detail.hasGeoUrdf && (
            <span className="menu-warn"> — export geometry first</span>
          )}
        </span>
      )}
    </div>
  );
}

function ViewToggle({
  label,
  storeKey,
}: {
  label: string;
  storeKey: "showCom" | "showInertiaAxes" | "showWholeCom";
}) {
  const active = useEditorStore((s) => s[storeKey]);
  const toggle =
    storeKey === "showCom"
      ? useEditorStore((s) => s.toggleCom)
      : storeKey === "showInertiaAxes"
        ? useEditorStore((s) => s.toggleInertiaAxes)
        : useEditorStore((s) => s.toggleWholeCom);

  return (
    <button type="button" className={`menu-entry full-width ${active ? "checked" : ""}`} onClick={toggle}>
      <span>{active ? "✓ " : ""}{label}</span>
    </button>
  );
}
