import { useState, type ReactNode } from "react";

export function Foldout({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="foldout">
      <button type="button" className="foldout-header" onClick={() => setOpen(!open)}>
        <span className={`foldout-arrow ${open ? "open" : ""}`} aria-hidden>
          &#9654;
        </span>
        <span>{title}</span>
      </button>
      {open && <div className="foldout-body">{children}</div>}
    </div>
  );
}
