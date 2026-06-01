import { useState } from "react";
import type { ProjectSummary } from "../../types";

type Props = {
  projects: string[];
  projectDetails: ProjectSummary[];
  active: string | null;
  onLoad: (name: string) => void;
};

export function MenuBar({ projects, projectDetails, active, onLoad }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="menu-bar">
      <div className="menu-brand">
        <span className="brand-mark" />
        QuadRL Train Monitor
      </div>
      <div className="menu-item">
        <button type="button" className="menu-btn" onClick={() => setOpen(!open)}>
          Project {active ? `· ${active}` : ""} ▾
        </button>
        {open && (
          <div className="menu-dropdown">
            {projects.length === 0 && <div className="menu-empty">No projects found</div>}
            {projects.map((name) => {
              const detail = projectDetails.find((d) => d.name === name);
              return (
                <button
                  key={name}
                  type="button"
                  className={`menu-dropdown-item ${active === name ? "active" : ""}`}
                  onClick={() => {
                    onLoad(name);
                    setOpen(false);
                  }}
                >
                  <span>{name}</span>
                  {detail && (
                    <span className="menu-meta">
                      {detail.export_count} exports · {detail.checkpoint_count} ckpt
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
