import type { ReactNode } from "react";

/** A titled panel card — the shared container for every region of the page. */
export function SectionCard({
  title,
  meta,
  actions,
  children,
  className = "",
}: {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`tp-card ${className}`}>
      <header className="tp-card-header">
        <h2>{title}</h2>
        <span className="tp-card-spacer" />
        {meta ? <span className="tp-card-meta">{meta}</span> : null}
        {actions}
      </header>
      <div className="tp-card-body">{children}</div>
    </section>
  );
}
