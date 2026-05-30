import { useState } from "react";
import type { CustomParamValue } from "@rl-trainer-model";
import { api } from "../../api/client";
import { useTrainerStore } from "../../stores/trainerStore";

export function CustomPanel() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const [newKey, setNewKey] = useState("");
  const [newVal, setNewVal] = useState("");
  const [newType, setNewType] = useState<"number" | "string" | "boolean">("number");

  if (!model) return null;

  const save = async (params: Record<string, CustomParamValue>) => {
    if (!project) return;
    try {
      setModel(await api.patchModel(project, { customParams: params }));
    } catch (e) {
      log(String(e));
    }
  };

  const parseValue = (): CustomParamValue => {
    if (newType === "boolean") return newVal === "true";
    if (newType === "number") return parseFloat(newVal) || 0;
    return newVal;
  };

  const addParam = () => {
    const key = newKey.trim();
    if (!key) return;
    void save({ ...model.customParams, [key]: parseValue() });
    setNewKey("");
    setNewVal("");
  };

  const removeParam = (key: string) => {
    const next = { ...model.customParams };
    delete next[key];
    void save(next);
  };

  const entries = Object.entries(model.customParams);

  return (
    <div className="tab-panel custom-panel">
      <p className="panel-hint">
        Forward-compatible key-value pairs exported under <code>custom_params</code> in YAML.
      </p>
      <div className="custom-add-row">
        <input
          className="param-input"
          placeholder="key"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
        />
        <select
          className="param-select"
          value={newType}
          onChange={(e) => setNewType(e.target.value as typeof newType)}
        >
          <option value="number">number</option>
          <option value="string">string</option>
          <option value="boolean">boolean</option>
        </select>
        <input
          className="param-input"
          placeholder="value"
          value={newVal}
          onChange={(e) => setNewVal(e.target.value)}
        />
        <button type="button" className="header-btn" onClick={addParam}>
          Add
        </button>
      </div>
      {entries.length === 0 ? (
        <p className="empty-desc">No custom parameters yet.</p>
      ) : (
        <ul className="custom-list">
          {entries.map(([key, val]) => (
            <li key={key} className="custom-row">
              <span className="mono custom-key">{key}</span>
              <span className="mono custom-val">{String(val)}</span>
              <button type="button" className="header-btn" onClick={() => removeParam(key)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
