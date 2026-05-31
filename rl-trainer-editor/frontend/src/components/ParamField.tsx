import type { ReactNode } from "react";
import { Checkbox } from "./Checkbox";

function ParamHint({ text }: { text?: string }) {
  if (!text) return null;
  return (
    <span className="param-hint-icon" title={text} aria-label={text}>
      ⓘ
    </span>
  );
}

export function ParamField({
  paramKey,
  label,
  hint,
  enabled,
  onEnabledChange,
  children,
}: {
  paramKey: string;
  label: string;
  hint?: string;
  enabled: boolean;
  onEnabledChange: (v: boolean) => void;
  children: ReactNode;
}) {
  const checkboxId = `param-${paramKey.replace(/[^a-z0-9.-]/gi, "-")}`;
  return (
    <div className={`param-field param-field-checked ${enabled ? "" : "param-disabled"}`}>
      <Checkbox
        id={checkboxId}
        checked={enabled}
        onChange={onEnabledChange}
        hint={hint ? `${label}: ${hint}` : label}
      />
      <label className="param-label-row" htmlFor={checkboxId}>
        <span className="param-label">{label}</span>
        <ParamHint text={hint} />
      </label>
      <div className="param-control">{children}</div>
    </div>
  );
}

export function ParamNumberField({
  paramKey,
  label,
  hint,
  enabled,
  onEnabledChange,
  value,
  onChange,
  step = 0.01,
  min,
  status,
}: {
  paramKey: string;
  label: string;
  hint?: string;
  enabled: boolean;
  onEnabledChange: (v: boolean) => void;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  status?: "ok" | "warn";
}) {
  return (
    <ParamField
      paramKey={paramKey}
      label={label}
      hint={hint}
      enabled={enabled}
      onEnabledChange={onEnabledChange}
    >
      <input
        type="number"
        className={`param-input ${status ? `param-${status}` : ""}`}
        step={step}
        min={min}
        disabled={!enabled}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </ParamField>
  );
}

export function ParamTextField({
  paramKey,
  label,
  hint,
  enabled,
  onEnabledChange,
  value,
  onChange,
}: {
  paramKey: string;
  label: string;
  hint?: string;
  enabled: boolean;
  onEnabledChange: (v: boolean) => void;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <ParamField paramKey={paramKey} label={label} hint={hint} enabled={enabled} onEnabledChange={onEnabledChange}>
      <input
        type="text"
        className="param-input"
        disabled={!enabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </ParamField>
  );
}

export function ParamBoolField({
  paramKey,
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  paramKey: string;
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  const checkboxId = `param-bool-${paramKey.replace(/[^a-z0-9.-]/gi, "-")}`;
  return (
    <div className={`param-field param-field-bool ${disabled ? "param-disabled" : ""}`}>
      <input
        id={checkboxId}
        type="checkbox"
        className="param-checkbox"
        checked={checked}
        disabled={disabled}
        title={hint ? `${label}: ${hint}` : label}
        onChange={(e) => onChange(e.target.checked)}
      />
      <label className="param-label-row" htmlFor={checkboxId}>
        <span className="param-label">{label}</span>
        <ParamHint text={hint} />
      </label>
    </div>
  );
}
