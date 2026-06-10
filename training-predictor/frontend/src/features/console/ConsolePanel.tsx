import { useEffect, useRef } from "react";
import { SectionCard } from "../../components/SectionCard";
import { useStudyStore } from "../../stores/studyStore";

/** Live log stream from the study, auto-scrolling while the user is at the bottom. */
export function ConsolePanel() {
  const logs = useStudyStore((s) => s.logs);
  const bodyRef = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  useEffect(() => {
    const el = bodyRef.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [logs]);

  return (
    <SectionCard title="Live log" meta={logs.length ? `${logs.length} lines` : undefined} className="tp-console-card">
      <div
        className="tp-console"
        ref={bodyRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollTop + el.clientHeight >= el.scrollHeight - 24;
        }}
      >
        {logs.length === 0 ? (
          <span className="tp-muted">Waiting for the study to start…</span>
        ) : (
          logs.map((e, i) => (
            <div key={i} className={`tp-logline tp-log-${e.level || "info"}`}>
              <span className="tp-log-level">{(e.level || "info").padEnd(7)}</span>
              {e.message}
            </div>
          ))
        )}
      </div>
    </SectionCard>
  );
}
