import type { MonitorPageId } from "../../types";

const PAGES: { id: MonitorPageId; label: string }[] = [
  { id: "spawn", label: "Spawn Monitor" },
  { id: "topic", label: "Topic Monitor" },
  { id: "training", label: "Training Monitor" },
  { id: "metric", label: "Metric Monitor" },
];

type Props = {
  active: MonitorPageId;
  onChange: (page: MonitorPageId) => void;
};

export function PageNav({ active, onChange }: Props) {
  return (
    <nav className="page-nav" aria-label="Monitor pages">
      {PAGES.map((p) => (
        <button
          key={p.id}
          type="button"
          className={`page-nav-btn ${active === p.id ? "active" : ""}`}
          aria-current={active === p.id ? "page" : undefined}
          onClick={() => onChange(p.id)}
        >
          {p.label}
        </button>
      ))}
    </nav>
  );
}
