import { useEffect, useRef, useState } from "react";
import { useTrainerStore } from "../../stores/trainerStore";

type Props = {
  projects: string[];
  projectDetails: { name: string; hasSensor: boolean; hasTrainer: boolean }[];
  onLoadProject: (name: string) => void;
  onBootstrap: () => void;
};

export function MenuBar({ projects, projectDetails, onLoadProject, onBootstrap }: Props) {
  const project = useTrainerStore((s) => s.project);
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
      <span className="menu-brand rl-brand">
        <span className="brand-mark" aria-hidden />
        RL Trainer
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
                <span className={`chip ${detail.hasSensor ? "ok" : "warn"}`}>
                  {detail.hasSensor ? "sensor pipeline" : "no sensor model"}
                </span>
                <span className={`chip ${detail.hasTrainer ? "ok" : ""}`}>
                  {detail.hasTrainer ? "trainer saved" : "new"}
                </span>
              </div>
            )}
            <hr />
            <button
              type="button"
              className="menu-entry"
              disabled={!project}
              onClick={() => {
                onBootstrap();
                setOpenMenu(null);
              }}
            >
              Bootstrap RL config
            </button>
          </div>
        )}
      </div>
      <span className="menu-spacer" />
      {project && <span className="menu-context mono">{project}</span>}
    </div>
  );
}
