export function MetricCard({
  label,
  value,
  sub,
  variant = "default",
  className,
}: {
  label: string;
  value: string;
  sub?: string;
  variant?: "default" | "accent" | "ok" | "warn" | "gpu";
  className?: string;
}) {
  return (
    <div className={`metric-card metric-${variant}${className ? ` ${className}` : ""}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {sub && <span className="metric-sub">{sub}</span>}
    </div>
  );
}
