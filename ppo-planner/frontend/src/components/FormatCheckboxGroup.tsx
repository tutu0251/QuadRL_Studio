import type { ExportConfigFormat } from "@ppo-model";
import { EXPORT_FORMAT_OPTIONS } from "@ppo-model";

export function FormatCheckboxGroup({
  selected,
  onChange,
}: {
  selected: ExportConfigFormat[];
  onChange: (formats: ExportConfigFormat[]) => void;
}) {
  const toggle = (id: ExportConfigFormat) => {
    const set = new Set(selected);
    if (set.has(id)) {
      if (set.size <= 1) return;
      set.delete(id);
    } else {
      set.add(id);
    }
    const order = EXPORT_FORMAT_OPTIONS.map((o) => o.id);
    onChange(order.filter((fmt) => set.has(fmt)));
  };

  return (
    <div className="format-checkbox-group" role="group" aria-label="Export formats">
      {EXPORT_FORMAT_OPTIONS.map((opt) => {
        const checked = selected.includes(opt.id);
        const onlyOne = checked && selected.length === 1;
        return (
          <label
            key={opt.id}
            className={`format-option ${checked ? "format-option-on" : ""}`}
            title={opt.description}
          >
            <input
              type="checkbox"
              checked={checked}
              disabled={onlyOne}
              onChange={() => toggle(opt.id)}
            />
            <span className="format-option-body">
              <span className="format-option-label">{opt.label}</span>
              <span className="format-option-ext mono">ppo_*{opt.filenameSuffix}</span>
            </span>
          </label>
        );
      })}
    </div>
  );
}
