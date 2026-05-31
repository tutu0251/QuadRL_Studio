import { GAIT_CATALOG_IDS, GAIT_PARAM_HINTS, type GaitType } from "@rl-trainer-model";
import { api } from "../../api/client";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { NumberField } from "../../components/NumberField";
import { useTrainerStore } from "../../stores/trainerStore";

const LEGS = ["fl", "fr", "rl", "rr"] as const;

export function GaitTypePanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const selectedGaitTypeId = useTrainerStore((s) => s.selectedGaitTypeId);
  const setSelectedGaitTypeId = useTrainerStore((s) => s.setSelectedGaitTypeId);
  const log = useTrainerStore((s) => s.log);

  if (!model || !project) return null;

  const gaits = model.gaitTypes ?? [];
  const gait = selectedGaitTypeId
    ? gaits.find((g) => g.id === selectedGaitTypeId)
    : gaits[0];

  const saveGaits = async (next: GaitType[]) => {
    try {
      setModel(await api.patchModel(project, { gaitTypes: next }));
    } catch (e) {
      log(String(e));
    }
  };

  const patchGait = (patch: Partial<GaitType>) => {
    if (!gait) return;
    const next = gaits.map((g) => (g.id === gait.id ? { ...g, ...patch } : g));
    void saveGaits(next);
  };

  const patchPhase = (leg: (typeof LEGS)[number], value: number) => {
    if (!gait) return;
    patchGait({ phaseOffsets: { ...gait.phaseOffsets, [leg]: value } });
  };

  const addFromCatalog = async (gaitId: string) => {
    try {
      setModel(await api.recommendGait(project, gaitId));
      setSelectedGaitTypeId(gaitId);
      log(`Added gait: ${gaitId}`);
    } catch (e) {
      log(String(e));
    }
  };

  const deleteGait = () => {
    if (!gait || gait.builtin) return;
    const next = gaits.filter((g) => g.id !== gait.id);
    void saveGaits(next);
    setSelectedGaitTypeId(next[0]?.id ?? null);
  };

  const recommend = async () => {
    if (!gait) return;
    try {
      setModel(await api.recommendGait(project, gait.id));
      log(`Recommended params for gait '${gait.name}'`);
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <div className="tab-panel gait-panel">
      <div className="gait-layout">
        <aside className="gait-library">
          <h4 className="section-label">Gait types</h4>
          {gaits.map((g) => (
            <button
              key={g.id}
              type="button"
              className={`library-item library-select ${gait?.id === g.id ? "selected" : ""}`}
              onClick={() => setSelectedGaitTypeId(g.id)}
            >
              <strong>{g.name}</strong>
              <span className="preset-meta mono">T={g.cycleTime}s · duty={g.dutyFactor}</span>
            </button>
          ))}
          <div className="catalog-add">
            <span className="section-label">Add from catalog</span>
            <div className="catalog-btns">
              {GAIT_CATALOG_IDS.filter((id) => !gaits.some((g) => g.id === id)).map((id) => (
                <button key={id} type="button" className="header-btn" onClick={() => void addFromCatalog(id)}>
                  + {id}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {gait ? (
          <div className="gait-editor">
            <div className="stage-panel-header">
              <h3>{gait.name}</h3>
              <div className="header-actions">
                <button type="button" className="header-btn" onClick={() => void recommend()}>Auto-recommend</button>
                {!gait.builtin && (
                  <button type="button" className="header-btn danger" onClick={deleteGait}>Delete</button>
                )}
              </div>
            </div>

            <CollapsibleSection id="gait-params" title="Parameters">
              <div className="param-field">
                <span className="param-label">name</span>
                <input className="param-input" value={gait.name} onChange={(e) => patchGait({ name: e.target.value })} />
              </div>
              <NumberField label="cycle_time" hint={GAIT_PARAM_HINTS.cycleTime} value={gait.cycleTime} step={0.01} onChange={(v) => patchGait({ cycleTime: v })} />
              <NumberField label="duty_factor" hint={GAIT_PARAM_HINTS.dutyFactor} value={gait.dutyFactor} step={0.05} onChange={(v) => patchGait({ dutyFactor: v })} />
              <NumberField label="swing_height" hint={GAIT_PARAM_HINTS.swingHeight} value={gait.swingHeight ?? 0} step={0.01} onChange={(v) => patchGait({ swingHeight: v })} />
              <NumberField label="step_length" hint={GAIT_PARAM_HINTS.stepLength} value={gait.stepLength ?? 0} step={0.01} onChange={(v) => patchGait({ stepLength: v })} />
              <NumberField label="body_height" hint={GAIT_PARAM_HINTS.bodyHeight} value={gait.bodyHeight ?? 0.35} step={0.01} onChange={(v) => patchGait({ bodyHeight: v })} />
            </CollapsibleSection>

            <CollapsibleSection id="phase-offsets" title="Phase offsets (FL FR RL RR)">
              <div className="phase-grid">
                {LEGS.map((leg) => (
                  <NumberField
                    key={leg}
                    label={leg}
                    value={gait.phaseOffsets[leg]}
                    step={0.05}
                    onChange={(v) => patchPhase(leg, v)}
                  />
                ))}
              </div>
            </CollapsibleSection>
          </div>
        ) : (
          <p className="empty-desc">Add a gait type from the catalog.</p>
        )}
      </div>
    </div>
  );
}
