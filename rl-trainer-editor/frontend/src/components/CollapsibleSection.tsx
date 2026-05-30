import { useState, type ReactNode } from "react";

export function CollapsibleSection({
  id,
  title,
  defaultOpen = true,
  badge,
  children,
}: {
  id: string;
  title: string;
  defaultOpen?: boolean;
  badge?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`collapsible-section ${open ? "open" : "collapsed"}`}>
      <button
        type="button"
        className="collapsible-header"
        aria-expanded={open}
        aria-controls={`section-${id}`}
        onClick={() => setOpen(!open)}
      >
        <span className="collapsible-chevron" aria-hidden>
          ▶
        </span>
        <span className="collapsible-title">{title}</span>
        {badge && <span className="collapsible-badge">{badge}</span>}
      </button>
      {open && (
        <div id={`section-${id}`} className="collapsible-body">
          {children}
        </div>
      )}
    </section>
  );
}
