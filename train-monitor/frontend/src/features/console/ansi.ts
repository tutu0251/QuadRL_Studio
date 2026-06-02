export type AnsiSegment = {
  text: string;
  className: string;
};

const ESC = "\u001b";

function pushSeg(out: AnsiSegment[], text: string, className: string) {
  if (!text) return;
  const last = out[out.length - 1];
  if (last && last.className === className) {
    last.text += text;
    return;
  }
  out.push({ text, className });
}

function normalizeCodes(codes: number[]): number[] {
  // Empty sequence means reset
  if (codes.length === 0) return [0];
  return codes;
}

function classForState(state: { bold: boolean; fg: string | null; dim: boolean }) {
  const classes: string[] = ["ansi"];
  if (state.bold) classes.push("ansi-bold");
  if (state.dim) classes.push("ansi-dim");
  if (state.fg) classes.push(`ansi-fg-${state.fg}`);
  return classes.join(" ");
}

function applySgr(state: { bold: boolean; fg: string | null; dim: boolean }, codes: number[]) {
  for (const code of normalizeCodes(codes)) {
    if (code === 0) {
      state.bold = false;
      state.dim = false;
      state.fg = null;
      continue;
    }
    if (code === 1) {
      state.bold = true;
      continue;
    }
    if (code === 2) {
      state.dim = true;
      continue;
    }
    if (code === 22) {
      state.bold = false;
      state.dim = false;
      continue;
    }
    if (code === 39) {
      state.fg = null;
      continue;
    }
    // Standard colors 30-37, bright 90-97
    const colorMap: Record<number, string> = {
      30: "black",
      31: "red",
      32: "green",
      33: "yellow",
      34: "blue",
      35: "magenta",
      36: "cyan",
      37: "white",
      90: "bright-black",
      91: "bright-red",
      92: "bright-green",
      93: "bright-yellow",
      94: "bright-blue",
      95: "bright-magenta",
      96: "bright-cyan",
      97: "bright-white",
    };
    if (colorMap[code]) {
      state.fg = colorMap[code];
    }
  }
}

/**
 * Parse ANSI SGR escapes (e.g. "\x1b[92m") into styled segments.
 * Unknown/control sequences are removed (but text is preserved).
 */
export function parseAnsiToSegments(input: string): AnsiSegment[] {
  const out: AnsiSegment[] = [];
  const state = { bold: false, dim: false, fg: null as string | null };

  let i = 0;
  while (i < input.length) {
    const escIdx = input.indexOf(ESC, i);
    if (escIdx === -1) {
      pushSeg(out, input.slice(i), classForState(state));
      break;
    }
    // push plain text before escape
    pushSeg(out, input.slice(i, escIdx), classForState(state));

    // Try parse CSI: ESC [ ... finalByte
    if (input[escIdx + 1] !== "[") {
      // Not a CSI sequence; skip the ESC char.
      i = escIdx + 1;
      continue;
    }
    const after = escIdx + 2;
    let j = after;
    while (j < input.length && !/[A-Za-z]/.test(input[j])) j += 1;
    if (j >= input.length) break;
    const final = input[j];
    const body = input.slice(after, j);

    // Only handle SGR (m). For others, just drop the sequence.
    if (final === "m") {
      const codes = body
        .split(";")
        .filter((x) => x.length > 0)
        .map((x) => Number.parseInt(x, 10))
        .filter((n) => Number.isFinite(n));
      applySgr(state, codes);
    }
    i = j + 1;
  }
  return out;
}

