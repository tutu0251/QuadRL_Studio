import { useTrainerStore } from "../../stores/trainerStore";
import { CurriculumPanel } from "../curriculum/CurriculumPanel";
import { GaitTypePanel } from "../gait/GaitTypePanel";
import { ObservationsPanel } from "../observations/ObservationsPanel";

const TABS = [
  { id: "curriculum", label: "Curriculum", hint: "Stages & training order" },
  { id: "gait", label: "Gate Type", hint: "None, walk, trot, gallop — cycle & phase params" },
  { id: "observations", label: "Observations", hint: "Policy vector size, layout, and per-term normalization" },
] as const;

export function InspectorTabs() {
  const activeTab = useTrainerStore((s) => s.activeTab);
  const setActiveTab = useTrainerStore((s) => s.setActiveTab);
  const model = useTrainerStore((s) => s.model);

  if (!model) {
    return (
      <div className="unity-panel inspector-tabs editor-primary">
        <div className="editor-empty-state">
          <div className="editor-empty-icon" aria-hidden>
            ◇
          </div>
          <h2>Open a project</h2>
          <p>Use File → select project to configure curriculum, gate types, and review observations.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="unity-panel inspector-tabs editor-primary">
      <div className="tab-bar tab-bar-segmented" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={activeTab === t.id}
            title={t.hint}
            className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content editor-tab-content">
        {activeTab === "curriculum" && <CurriculumPanel />}
        {activeTab === "gait" && <GaitTypePanel />}
        {activeTab === "observations" && <ObservationsPanel />}
      </div>
    </div>
  );
}
