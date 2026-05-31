import type { ReactNode } from "react";

export function SectionCard({
  title,
  description,
  disabled,
  children,
}: {
  title: string;
  description?: string;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={`section-card ${disabled ? "section-disabled" : ""}`}>
      <header className="section-card-header">
        <h4>{title}</h4>
        {description && <p>{description}</p>}
      </header>
      <div className="section-card-body">{children}</div>
    </section>
  );
}
