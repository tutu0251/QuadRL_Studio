import { useCallback, useState } from "react";

export function useClampedSize(initial: number, min: number, max: number) {
  const [size, setSize] = useState(initial);

  const resizeBy = useCallback(
    (delta: number) => {
      setSize((prev) => Math.min(max, Math.max(min, prev + delta)));
    },
    [min, max]
  );

  return [size, resizeBy] as const;
}
