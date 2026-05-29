import type { CollisionFriction } from "@robot-model";

type FrictionFlag = "useMu" | "useMu2" | "useKp" | "useKd";
type FrictionValue = "mu" | "mu2" | "kp" | "kd";

export function FrictionParamRow({
  label,
  flag,
  valueKey,
  friction,
  onChange,
  panelEnabled,
  step = 0.01,
  min,
}: {
  label: string;
  flag: FrictionFlag;
  valueKey: FrictionValue;
  friction: CollisionFriction;
  onChange: (fr: CollisionFriction) => void;
  panelEnabled: boolean;
  step?: number;
  min?: number;
}) {
  const paramOn = panelEnabled && friction[flag];
  const inputDisabled = !paramOn;

  return (
    <div className={`friction-param-row ${paramOn ? "enabled" : "ignored"}`}>
      <button
        type="button"
        className={`param-toggle ${paramOn ? "on" : "off"}`}
        disabled={!panelEnabled}
        onClick={() => onChange({ ...friction, [flag]: !friction[flag] })}
        title={
          !panelEnabled
            ? "Enable collision friction for this link first"
            : paramOn
              ? "Included in export"
              : "Ignored (simulator default)"
        }
        aria-pressed={paramOn}
      >
        {paramOn ? "ON" : "—"}
      </button>
      <label className="friction-param-field">
        <span className="field-label">{label}</span>
        <input
          type="number"
          step={step}
          min={min}
          disabled={inputDisabled}
          value={friction[valueKey]}
          onChange={(e) =>
            onChange({ ...friction, [valueKey]: parseFloat(e.target.value) || 0 })
          }
        />
      </label>
    </div>
  );
}
