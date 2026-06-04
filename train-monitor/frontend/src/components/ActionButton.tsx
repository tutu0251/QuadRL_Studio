import type { ButtonHTMLAttributes, ReactNode } from "react";
import { CommandPreview } from "./CommandPreview";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  command?: string | null;
  commandLoading?: boolean;
  children: ReactNode;
};

export function ActionButton({ command, commandLoading, children, className, ...rest }: Props) {
  return (
    <div className="action-button-wrap">
      <button type="button" className={className ?? "btn"} {...rest}>
        {children}
      </button>
      <CommandPreview command={command} loading={commandLoading} />
    </div>
  );
}
