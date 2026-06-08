import type { ReactNode } from "react";
import { Checkbox } from "./Checkbox";
import { NumericInput } from "./NumericInput";

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
    <article className={`inspector-param-card ${enabled ? "" : "param-disabled"}`}>
      <header className="inspector-param-card-head">
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
      </header>
      <div className="inspector-param-card-body">{children}</div>
    </article>
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
      <NumericInput
        className={`param-input ${status ? `param-${status}` : ""}`}
        step={step}
        min={min}
        disabled={!enabled}
        value={value}
        onCommit={onChange}
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

export function ParamSelectField({
  paramKey,
  label,
  hint,
  enabled,
  onEnabledChange,
  value,
  onChange,
  options,
}: {
  paramKey: string;
  label: string;
  hint?: string;
  enabled: boolean;
  onEnabledChange: (v: boolean) => void;
  value: string;
  onChange: (v: string) => void;
  options: { id: string; name: string }[];
}) {
  return (
    <ParamField paramKey={paramKey} label={label} hint={hint} enabled={enabled} onEnabledChange={onEnabledChange}>
      <select className="param-input param-select" disabled={!enabled} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </ParamField>
  );
}

export function ParamMultiSelectField({
  paramKey,
  label,
  hint,
  enabled,
  onEnabledChange,
  value,
  onChange,
  options,
}: {
  paramKey: string;
  label: string;
  hint?: string;
  enabled: boolean;
  onEnabledChange: (v: boolean) => void;
  value: string[];
  onChange: (v: string[]) => void;
  options: { id: string; name: string }[];
}) {
  const toggle = (id: string) => {
    if (value.includes(id)) {
      if (value.length <= 1) return;
      onChange(value.filter((x) => x !== id));
    } else {
      onChange([...value, id]);
    }
  };

  return (
    <ParamField paramKey={paramKey} label={label} hint={hint} enabled={enabled} onEnabledChange={onEnabledChange}>
      <div className="chip-row param-multi-select" role="group" aria-label={label}>
        {options.map((o) => {
          const selected = value.includes(o.id);
          return (
            <button
              key={o.id}
              type="button"
              className={`chip-btn ${selected ? "active" : ""}`}
              disabled={!enabled}
              aria-pressed={selected}
              onClick={() => toggle(o.id)}
            >
              {o.name}
            </button>
          );
        })}
      </div>
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
    <article className={`inspector-param-card inspector-param-card-bool ${disabled ? "param-disabled" : ""}`}>
      <header className="inspector-param-card-head">
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
      </header>
    </article>
  );
}
