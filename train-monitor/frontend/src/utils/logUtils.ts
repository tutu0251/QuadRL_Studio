import type { LogEntry, LogLevel } from "../types";

const LEVELS: LogLevel[] = ["debug", "info", "warn", "error"];

export function normalizeLogLevel(raw: string): LogLevel {
  const key = raw.toLowerCase();
  if (LEVELS.includes(key as LogLevel)) return key as LogLevel;
  if (key === "warning") return "warn";
  if (key === "critical" || key === "fatal") return "error";
  return "info";
}

/** Extract a bracketed prefix like `[workspace]` as the log component. */
export function parseLogComponent(message: string): string | undefined {
  const match = message.match(/^\[([^\]]+)\]\s*/);
  return match?.[1];
}

export function inferLogLevel(message: string): LogLevel {
  const lower = message.toLowerCase();
  if (lower.includes("[error]") || lower.includes("failed") || lower.includes("traceback"))
    return "error";
  if (lower.includes("warn") || lower.includes("⚠")) return "warn";
  if (lower.includes("debug")) return "debug";
  return "info";
}

export function formatLogTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function createLogEntry(
  message: string,
  options?: { level?: LogLevel; component?: string; timestamp?: string }
): Omit<LogEntry, "id"> {
  const component = options?.component ?? parseLogComponent(message);
  return {
    timestamp: options?.timestamp ?? new Date().toISOString(),
    level: options?.level ?? inferLogLevel(message),
    message,
    ...(component ? { component } : {}),
  };
}

export function nextLogId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
