import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { CommandPreview } from "../types";

export function useCommandPreview(
  project: string | null,
  action: string,
  params?: Record<string, unknown>,
  enabled = true
) {
  const [preview, setPreview] = useState<CommandPreview | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!project || !enabled || !action) {
      setPreview(null);
      return;
    }
    setLoading(true);
    try {
      const p = await api.getCommandPreview(project, action, params);
      setPreview(p);
    } catch {
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }, [project, action, enabled, JSON.stringify(params ?? {})]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { preview, loading, refresh };
}
