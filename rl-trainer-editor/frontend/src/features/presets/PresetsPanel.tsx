import { useEffect, useState } from "react";
import { PRESET_CATALOG, type PresetInfo } from "@rl-trainer-model";
import { api } from "../../api/client";
import { Toggle } from "../../components/Toggle";
import { useTrainerStore } from "../../stores/trainerStore";

export function PresetsPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const [presets, setPresets] = useState<PresetInfo[]>(PRESET_CATALOG);

  useEffect(() => {
    api.presets().then((r) => setPresets(r.presets)).catch(() => {});
  }, []);

  const applyPreset = async (presetId: string) => {
    if (!project) return;
    try {
      const m = await api.applyPreset(project, presetId);
      setModel(m);
      log(`Applied preset: ${presetId}`);
    } catch (e) {
      log(String(e));
    }
  };

  if (!model) return null;

  return (
    <div className="tab-panel presets-panel">
      <div className="panel-row">
        <Toggle
          label="Auto-apply machine recommendations"
          checked={model.useRecommended}
          onChange={(v) =>
            void (async () => {
              if (!project) return;
              setModel(await api.patchModel(project, { useRecommended: v }));
            })()
          }
        />
      </div>
      <div className="preset-grid">
        {presets.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`preset-card ${model.selectedPresetId === p.id ? "selected" : ""}`}
            onClick={() => void applyPreset(p.id)}
          >
            <span className={`preset-diff preset-${p.difficulty}`}>{p.difficulty}</span>
            <strong>{p.name}</strong>
            <p>{p.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
