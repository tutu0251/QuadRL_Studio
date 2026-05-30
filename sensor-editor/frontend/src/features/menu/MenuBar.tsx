import { useEffect, useRef, useState } from "react";
import { useEditorStore } from "../../stores/editorStore";

type Props = {
  projects: string[];
  projectDetails: { name: string; hasCtrlUrdf: boolean; hasSensor: boolean }[];
  onLoadProject: (name: string) => void;
  onImport: () => void;
  onBootstrap: () => void;
  onReload: () => void;
};

export function MenuBar({
  projects,
  projectDetails,
  onLoadProject,
  onImport,
  onBootstrap,
  onReload,
}: Props) {
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
      <span className="menu-brand control-brand">
        <span className="brand-mark" aria-hidden />
        Sensor
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
                <span className={`chip ${detail.hasCtrlUrdf ? "ok" : "warn"}`}>
                  {detail.hasCtrlUrdf ? "ctrl URDF" : "no ctrl URDF"}
                </span>
                <span className={`chip ${detail.hasSensor ? "ok" : ""}`}>
                  {detail.hasSensor ? "sensor saved" : "not imported"}
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
              Import ctrl URDF…
            </button>
            <button
              type="button"
              className="menu-entry full-width"
              disabled={!project}
              onClick={() => {
                onBootstrap();
                setOpenMenu(null);
              }}
            >
              Bootstrap quadruped sensors
              <span className="menu-entry-meta">IMU + foot contacts</span>
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
          </div>
        )}
      </div>

      <span className="menu-spacer" />
      {project && (
        <span className="menu-context">
          {project}
          {detail && !detail.hasCtrlUrdf && (
            <span className="menu-warn"> — export control package first</span>
          )}
        </span>
      )}
    </div>
  );
}
