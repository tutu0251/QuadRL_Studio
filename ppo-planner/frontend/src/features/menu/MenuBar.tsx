import { useEffect, useRef, useState } from "react";
import { usePlannerStore } from "../../stores/plannerStore";

type Props = {
  projects: string[];
  projectDetails: { name: string; hasSensor: boolean; hasPpo: boolean }[];
  onLoadProject: (name: string) => void;
  onBootstrap: () => void;
  onResetBaseline: () => void;
};

export function MenuBar({
  projects,
  projectDetails,
  onLoadProject,
  onBootstrap,
  onResetBaseline,
}: Props) {
  const project = usePlannerStore((s) => s.project);
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
      <span className="menu-brand ppo-brand">
        <span className="brand-mark" aria-hidden />
        PPO Planner
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
                <span className={`chip ${detail.hasPpo ? "ok" : ""}`}>
                  {detail.hasPpo ? "ppo saved" : "new"}
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
              Bootstrap PPO config
            </button>
            <button
              type="button"
              className="menu-entry"
              disabled={!project}
              onClick={() => {
                onResetBaseline();
                setOpenMenu(null);
              }}
            >
              Reset to SB3 baseline
            </button>
          </div>
        )}
      </div>

      <div className="menu-item">
        <button type="button" className="menu-btn" onClick={toggle("help")}>
          Help
        </button>
        {openMenu === "help" && (
          <div className="menu-dropdown menu-dropdown-wide">
            <p className="menu-help-title">Quick tips</p>
            <ul className="menu-help-list">
              <li>
                <strong>Recommend</strong> profiles CPU, RAM, and GPU, then sets rollout batch
                sizes.
              </li>
              <li>
                <strong>Validate</strong> checks ranges and batch divisibility before export.
              </li>
              <li>
                <strong>Output</strong> tab sets checkpoints, best model tracking, and YAML/JSON export.
              </li>
              <li>
                Disable <em>Auto-apply</em> in the inspector to keep manual overrides when
                re-recommending.
              </li>
            </ul>
            <p className="menu-help-meta">API :8004 · UI :5177</p>
          </div>
        )}
      </div>

      <span className="menu-spacer" />
      {project && <span className="menu-context mono">{project}</span>}
    </div>
  );
}
