import { useState } from "react";
import { usePlannerStore } from "../../stores/plannerStore";
import { ParamsPanel } from "../params/ParamsPanel";
import { ParallelPanel } from "../parallel/ParallelPanel";
import { OutputPanel } from "../output/OutputPanel";

const TABS = [
  { id: "hyperparams", label: "Hyperparams", desc: "PPO rollout & optimizer" },
  { id: "parallel", label: "Parallel", desc: "Vec env workers" },
  { id: "output", label: "Output", desc: "Checkpoints & export" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function InspectorTabs() {
  const model = usePlannerStore((s) => s.model);
  const validation = usePlannerStore((s) => s.validation);
  const [activeTab, setActiveTab] = useState<TabId>("hyperparams");

  if (!model) {
    return (
      <div className="unity-panel inspector-shell">
        <div className="panel-header">
          <span>Configuration</span>
        </div>
        <div className="panel-empty-state inspector-empty">
          <div className="empty-illustration" aria-hidden>
            ◈
          </div>
          <p className="empty-title">No project loaded</p>
          <p className="empty-desc">File → select a project to tune PPO settings</p>
        </div>
      </div>
    );
  }

  const activeMeta = TABS.find((t) => t.id === activeTab);

  return (
    <div className="unity-panel inspector-shell">
      <div className="inspector-head">
        <div>
          <span className="inspector-head-title">Inspector</span>
          <span className="inspector-head-sub">{activeMeta?.desc}</span>
        </div>
        {validation && (
          <span className={`inspector-status ${validation.valid ? "ok" : "err"}`}>
            {validation.valid ? "Valid" : `${validation.errors.length} issues`}
          </span>
        )}
      </div>

      <div className="tab-bar tab-bar-pill">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tab-btn tab-btn-pill ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === "hyperparams" && <ParamsPanel embedded />}
        {activeTab === "parallel" && <ParallelPanel />}
        {activeTab === "output" && <OutputPanel />}
      </div>
    </div>
  );
}
