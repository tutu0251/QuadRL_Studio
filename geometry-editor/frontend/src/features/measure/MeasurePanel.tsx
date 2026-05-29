import { useState } from "react";
import type { MeasurementResult } from "@robot-model";
import { useEditorStore } from "../../stores/editorStore";
import { api } from "../../api/client";

export function MeasurePanel() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const setMeasurement = useEditorStore((s) => s.setMeasurement);
  const log = useEditorStore((s) => s.log);
  const [linkA, setLinkA] = useState("");
  const [linkB, setLinkB] = useState("");
  const [jointA, setJointA] = useState("");
  const [jointB, setJointB] = useState("");
  const [result, setResult] = useState<MeasurementResult | null>(null);

  const apply = (r: MeasurementResult) => {
    setResult(r);
    setMeasurement(r);
    log(`${r.label}: ${r.value.toFixed(4)} ${r.unit}`);
  };

  const measure = async (fn: () => Promise<MeasurementResult>) => {
    if (!project) return;
    try {
      apply(await fn());
    } catch (e) {
      log(String(e));
    }
  };

  if (!model) return null;

  return (
      <section className="measure-compact">
        <h2>Measure</h2>
      <label>
        Link A
        <select value={linkA} onChange={(e) => setLinkA(e.target.value)}>
          <option value="">—</option>
          {model.links.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Link B
        <select value={linkB} onChange={(e) => setLinkB(e.target.value)}>
          <option value="">—</option>
          {model.links.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </label>
      <div className="btn-row">
        <button
          type="button"
          disabled={!linkA || !linkB}
          onClick={() => measure(() => api.measureDistance(project!, linkA, linkB))}
        >
          Distance
        </button>
        <button
          type="button"
          disabled={!linkA}
          onClick={() => measure(() => api.measureHeight(project!, linkA))}
        >
          Height
        </button>
        <button
          type="button"
          disabled={!linkB}
          onClick={() => measure(() => api.measureLinkLength(project!, linkB))}
        >
          Link length
        </button>
        <button
          type="button"
          disabled={!linkA || !linkB}
          onClick={() => measure(() => api.measureLegReach(project!, linkA, linkB))}
        >
          Leg reach
        </button>
      </div>
      <label>
        Joint A
        <select value={jointA} onChange={(e) => setJointA(e.target.value)}>
          <option value="">—</option>
          {model.joints.map((j) => (
            <option key={j.id} value={j.id}>
              {j.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Joint B
        <select value={jointB} onChange={(e) => setJointB(e.target.value)}>
          <option value="">—</option>
          {model.joints.map((j) => (
            <option key={j.id} value={j.id}>
              {j.name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        disabled={!jointA || !jointB}
        onClick={() => measure(() => api.measureAngle(project!, jointA, jointB))}
      >
        Angle between axes
      </button>
      {result && (
        <p className="measure-result">
          {result.label}: <strong>{result.value.toFixed(4)}</strong> {result.unit}
        </p>
      )}
    </section>
  );
}
