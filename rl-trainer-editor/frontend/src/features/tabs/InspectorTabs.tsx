import { useTrainerStore } from "../../stores/trainerStore";
import { CurriculumPanel } from "../curriculum/CurriculumPanel";
import { GaitTypePanel } from "../gait/GaitTypePanel";
import { StageEditorPanel } from "../stage/StageEditorPanel";

const TABS = [
  { id: "curriculum", label: "Curriculum" },
  { id: "stage", label: "Stage" },
  { id: "gait", label: "Gait" },
] as const;

export function InspectorTabs() {
  const activeTab = useTrainerStore((s) => s.activeTab);
  const setActiveTab = useTrainerStore((s) => s.setActiveTab);
  const model = useTrainerStore((s) => s.model);
  const validation = useTrainerStore((s) => s.validation);

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

  const warnCount = validation?.warnings.length ?? 0;
  const errCount = validation?.errors.length ?? 0;

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
        {validation && (
          <span className={`tab-validation ${validation.valid ? "ok" : "err"}`}>
            {validation.valid ? (warnCount ? `${warnCount} warn` : "OK") : `${errCount} err`}
          </span>
        )}
      </div>
      <div className="tab-content">
        {activeTab === "curriculum" && <CurriculumPanel />}
        {activeTab === "stage" && <StageEditorPanel />}
        {activeTab === "gait" && <GaitTypePanel />}
      </div>
    </div>
  );
}
