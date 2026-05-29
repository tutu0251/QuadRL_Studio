import { useCallback, useRef } from "react";

type Axis = "horizontal" | "vertical";

type Props = {
  axis: Axis;
  onResize: (delta: number) => void;
};

export function ResizeHandle({ axis, onResize }: Props) {
  const dragging = useRef(false);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      dragging.current = true;
      const target = e.currentTarget;
      target.setPointerCapture(e.pointerId);
      document.body.style.cursor = axis === "horizontal" ? "col-resize" : "row-resize";
      document.body.style.userSelect = "none";
    },
    [axis]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging.current) return;
      const delta = axis === "horizontal" ? e.movementX : e.movementY;
      if (delta !== 0) onResize(delta);
    },
    [axis, onResize]
  );

  const endDrag = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return;
    dragging.current = false;
    e.currentTarget.releasePointerCapture(e.pointerId);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  return (
    <div
      className={`resize-handle resize-handle-${axis}`}
      role="separator"
      aria-orientation={axis === "horizontal" ? "vertical" : "horizontal"}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
    />
  );
}
