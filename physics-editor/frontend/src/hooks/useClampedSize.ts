import { useCallback, useState } from "react";

export function useClampedSize(initial: number, min: number, max: number) {
  const [size, setSize] = useState(initial);
  const resize = useCallback(
    (delta: number) => setSize((s) => Math.min(max, Math.max(min, s + delta))),
    [min, max]
  );
  return [size, resize] as const;
}
