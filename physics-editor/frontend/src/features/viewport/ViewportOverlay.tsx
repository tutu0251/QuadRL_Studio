import { useEditorStore } from "../../stores/editorStore";

function TogglePill({
  label,
  active,
  onClick,
  color,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  color?: string;
}) {
  return (
    <button
      type="button"
      className={`overlay-toggle ${active ? "active" : ""}`}
      onClick={onClick}
      style={color && active ? { borderColor: color } : undefined}
    >
      <span className="overlay-dot" style={color ? { background: color } : undefined} />
      {label}
    </button>
  );
}

export function ViewportOverlay() {
  const project = useEditorStore((s) => s.project);
  const model = useEditorStore((s) => s.model);
  const showCom = useEditorStore((s) => s.showCom);
  const showAxes = useEditorStore((s) => s.showInertiaAxes);
  const showWhole = useEditorStore((s) => s.showWholeCom);
  const wholeCom = useEditorStore((s) => s.wholeCom);
  const toggleCom = useEditorStore((s) => s.toggleCom);
  const toggleAxes = useEditorStore((s) => s.toggleInertiaAxes);
  const toggleWhole = useEditorStore((s) => s.toggleWholeCom);

  const totalMass = model?.links.reduce((s, l) => s + l.inertial.mass, 0) ?? 0;

  return (
    <>
      <div className="viewport-overlay viewport-overlay-tl">
        <div className="viewport-title">Scene</div>
        {project && (
          <div className="viewport-subtitle">
            {project} · {model?.links.length ?? 0} links · {totalMass.toFixed(2)} kg
          </div>
        )}
      </div>

      <div className="viewport-overlay viewport-overlay-tr">
        <div className="overlay-group">
          <span className="overlay-group-label">Overlays</span>
          <TogglePill label="Link COM" active={showCom} onClick={toggleCom} color="#ff8800" />
          <TogglePill label="Inertia axes" active={showAxes} onClick={toggleAxes} />
          <TogglePill label="Robot COM" active={showWhole} onClick={toggleWhole} color="#00cccc" />
        </div>
      </div>

      <div className="viewport-overlay viewport-overlay-bl">
        <div className="viewport-legend">
          <div className="legend-title">Inertia principal axes</div>
          <div className="legend-row">
            <span className="legend-swatch axis-x" /> I₁
          </div>
          <div className="legend-row">
            <span className="legend-swatch axis-y" /> I₂
          </div>
          <div className="legend-row">
            <span className="legend-swatch axis-z" /> I₃
          </div>
          <div className="legend-row muted">
            <span className="legend-swatch com" /> Link COM
          </div>
          <div className="legend-row muted">
            <span className="legend-swatch robot-com" /> Robot COM
            {wholeCom && showWhole && (
              <span className="legend-values">
                ({wholeCom.x.toFixed(3)}, {wholeCom.y.toFixed(3)}, {wholeCom.z.toFixed(3)}) m
              </span>
            )}
          </div>
        </div>
      </div>

      {!model?.links.length && (
        <div className="viewport-empty-hint">
          <p>Import <code>geo_&lt;project&gt;.urdf</code> from the File menu to begin.</p>
        </div>
      )}
    </>
  );
}
