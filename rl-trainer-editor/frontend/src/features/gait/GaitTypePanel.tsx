import { GAIT_CATALOG_IDS, GAIT_PARAM_HINTS, type GaitType } from "@rl-trainer-model";
import { api } from "../../api/client";
import { NumberField } from "../../components/NumberField";
import { useTrainerStore } from "../../stores/trainerStore";

const LEGS = ["fl", "fr", "rl", "rr"] as const;

function GaitTypeCard({
  gait,
  onPatch,
  onRecommend,
  onDelete,
}: {
  gait: GaitType;
  onPatch: (patch: Partial<GaitType>) => void;
  onRecommend: () => void;
  onDelete: () => void;
}) {
  const patchPhase = (leg: (typeof LEGS)[number], value: number) => {
    onPatch({ phaseOffsets: { ...gait.phaseOffsets, [leg]: value } });
  };

  return (
    <article className="gait-type-card inspector-param-card" aria-label={`Gate type ${gait.name}`}>
      <header className="gait-type-card-head">
        <div className="gait-type-card-title-block">
          <input
            type="text"
            className="gait-type-card-name"
            value={gait.name}
            aria-label={`${gait.id} display name`}
            onChange={(e) => onPatch({ name: e.target.value })}
          />
          <span className="gait-type-card-meta mono">
            {gait.id}
            {gait.builtin ? " · built-in" : ""}
          </span>
        </div>
        <div className="gait-type-card-actions">
          <button type="button" className="header-btn" onClick={onRecommend}>
            Recommend
          </button>
          {!gait.builtin && (
            <button type="button" className="header-btn danger" onClick={onDelete}>
              Delete
            </button>
          )}
        </div>
      </header>

      <div className="gait-type-card-body">
        <div className="gait-type-card-section">
          <h5 className="gait-type-card-section-title">Parameters</h5>
          <div className="gait-type-card-fields">
            <NumberField
              label="cycle_time"
              hint={GAIT_PARAM_HINTS.cycleTime}
              value={gait.cycleTime}
              step={0.01}
              onChange={(v) => onPatch({ cycleTime: v })}
            />
            <NumberField
              label="duty_factor"
              hint={GAIT_PARAM_HINTS.dutyFactor}
              value={gait.dutyFactor}
              step={0.05}
              onChange={(v) => onPatch({ dutyFactor: v })}
            />
            <NumberField
              label="swing_height"
              hint={GAIT_PARAM_HINTS.swingHeight}
              value={gait.swingHeight ?? 0}
              step={0.01}
              onChange={(v) => onPatch({ swingHeight: v })}
            />
            <NumberField
              label="step_length"
              hint={GAIT_PARAM_HINTS.stepLength}
              value={gait.stepLength ?? 0}
              step={0.01}
              onChange={(v) => onPatch({ stepLength: v })}
            />
            <NumberField
              label="body_height"
              hint={GAIT_PARAM_HINTS.bodyHeight}
              value={gait.bodyHeight ?? 0.35}
              step={0.01}
              onChange={(v) => onPatch({ bodyHeight: v })}
            />
          </div>
        </div>

        <div className="gait-type-card-section">
          <h5 className="gait-type-card-section-title">Phase offsets</h5>
          <p className="field-hint">FL · FR · RL · RR (0–1 cycle)</p>
          <div className="gait-type-card-phase-grid">
            {LEGS.map((leg) => (
              <NumberField
                key={leg}
                label={leg.toUpperCase()}
                value={gait.phaseOffsets[leg]}
                step={0.05}
                onChange={(v) => patchPhase(leg, v)}
              />
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}

function GaitAddCard({ gaitId, onAdd }: { gaitId: string; onAdd: () => void }) {
  return (
    <article className="gait-type-card gait-type-card-add">
      <button type="button" className="gait-type-add-btn" onClick={onAdd}>
        <span className="gait-type-add-label">+ {gaitId}</span>
        <span className="gait-type-add-hint">Add preset gate type</span>
      </button>
    </article>
  );
}

export function GaitTypePanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);

  if (!model || !project) return null;

  const gaits = model.gaitTypes ?? [];

  const saveGaits = async (next: GaitType[]) => {
    try {
      setModel(await api.patchModel(project, { gaitTypes: next }));
    } catch (e) {
      log(String(e));
    }
  };

  const patchGait = (gaitId: string, patch: Partial<GaitType>) => {
    const next = gaits.map((g) => (g.id === gaitId ? { ...g, ...patch } : g));
    void saveGaits(next);
  };

  const addFromCatalog = async (gaitId: string) => {
    try {
      setModel(await api.recommendGait(project, gaitId));
      log(`Added gait: ${gaitId}`);
    } catch (e) {
      log(String(e));
    }
  };

  const deleteGait = (gaitId: string) => {
    const target = gaits.find((g) => g.id === gaitId);
    if (!target || target.builtin) return;
    void saveGaits(gaits.filter((g) => g.id !== gaitId));
  };

  const recommendGait = async (gaitId: string) => {
    try {
      setModel(await api.recommendGait(project, gaitId));
      log(`Recommended params for gait '${gaitId}'`);
    } catch (e) {
      log(String(e));
    }
  };

  const missingCatalog = GAIT_CATALOG_IDS.filter((id) => !gaits.some((g) => g.id === id));

  return (
    <div className="tab-panel gait-panel">
      <div className="gait-cards-header pane-header">
        <h4 className="pane-title">Gate types</h4>
        <span className="pane-badge">{gaits.length}</span>
      </div>
      <div className="gait-cards-scroll editor-scroll">
        <div className="gait-cards-grid">
          {gaits.map((g) => (
            <GaitTypeCard
              key={g.id}
              gait={g}
              onPatch={(patch) => patchGait(g.id, patch)}
              onRecommend={() => void recommendGait(g.id)}
              onDelete={() => deleteGait(g.id)}
            />
          ))}
          {missingCatalog.map((id) => (
            <GaitAddCard key={id} gaitId={id} onAdd={() => void addFromCatalog(id)} />
          ))}
        </div>
        {gaits.length === 0 && missingCatalog.length === 0 && (
          <div className="editor-empty-state compact">
            <p className="empty-desc">No gate types configured.</p>
          </div>
        )}
      </div>
    </div>
  );
}
