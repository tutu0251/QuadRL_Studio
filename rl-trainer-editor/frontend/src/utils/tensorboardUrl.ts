/** Prefer API URL; fall back to the browser hostname for remote SSH / LAN access. */
export function resolveTensorboardUrl(apiUrl: string, port = 6006): string {
  try {
    const parsed = new URL(apiUrl);
    if (parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1") {
      return parsed.toString().replace(/\/$/, "");
    }
  } catch {
    /* ignore malformed API URL */
  }
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:${port}`;
}
