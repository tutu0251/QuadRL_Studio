import { useState, ReactNode } from "react";

interface Props {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function Foldout({ title, defaultOpen = true, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="foldout">
      <button type="button" className="foldout-header" onClick={() => setOpen(!open)}>
        <span className={`foldout-arrow ${open ? "open" : ""}`}>&#9654;</span>
        <span>{title}</span>
      </button>
      {open && <div className="foldout-body">{children}</div>}
    </div>
  );
}
