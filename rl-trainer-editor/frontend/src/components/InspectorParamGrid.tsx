import type { ReactNode } from "react";

export function InspectorParamGrid({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`inspector-param-grid ${className}`.trim()}>{children}</div>;
}
