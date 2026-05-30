import { useTrainerStore } from "../../stores/trainerStore";
import { PresetsPanel } from "../presets/PresetsPanel";
import { RewardsPanel } from "../rewards/RewardsPanel";
import { TerminationPanel } from "../termination/TerminationPanel";
import { HyperparamsPanel } from "../params/HyperparamsPanel";
import { ParallelPanel } from "../parallel/ParallelPanel";
import { CustomPanel } from "../custom/CustomPanel";
import { CurriculumPanel } from "../curriculum/CurriculumPanel";

const TABS = [
  { id: "presets", label: "Presets" },
  { id: "curriculum", label: "Curriculum" },
  { id: "rewards", label: "Rewards" },
  { id: "termination", label: "Termination" },
  { id: "hyperparams", label: "Hyperparams" },
  { id: "parallel", label: "Parallel" },
  { id: "custom", label: "Custom" },
] as const;

export function InspectorTabs() {
  const activeTab = useTrainerStore((s) => s.activeTab);
  const setActiveTab = useTrainerStore((s) => s.setActiveTab);
  const model = useTrainerStore((s) => s.model);

  if (!model) {
    return (
      <div className="unity-panel params-panel">
        <div className="panel-header">Configuration</div>
        <div className="panel-empty-state">
          <p className="empty-desc">Select a project to configure RL training</p>
        </div>
      </div>
    );
  }

  return (
    <div className="unity-panel inspector-tabs">
      <div className="tab-bar">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="tab-content">
        {activeTab === "presets" && <PresetsPanel />}
        {activeTab === "curriculum" && <CurriculumPanel />}
        {activeTab === "rewards" && <RewardsPanel />}
        {activeTab === "termination" && <TerminationPanel />}
        {activeTab === "hyperparams" && <HyperparamsPanel />}
        {activeTab === "parallel" && <ParallelPanel />}
        {activeTab === "custom" && <CustomPanel />}
      </div>
    </div>
  );
}
