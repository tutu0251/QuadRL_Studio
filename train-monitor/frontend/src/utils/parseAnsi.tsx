import type { ReactNode } from "react";

const ANSI_RE = /\x1b\[([0-9;]*)m/g;

type StyleState = {
  bold: boolean;
  dim: boolean;
  italic: boolean;
  fg?: string;
  bg?: string;
};

const FG_CLASSES: Record<number, string> = {
  30: "ansi-fg-black",
  31: "ansi-fg-red",
  32: "ansi-fg-green",
  33: "ansi-fg-yellow",
  34: "ansi-fg-blue",
  35: "ansi-fg-magenta",
  36: "ansi-fg-cyan",
  37: "ansi-fg-white",
  90: "ansi-fg-bright-black",
  91: "ansi-fg-bright-red",
  92: "ansi-fg-bright-green",
  93: "ansi-fg-bright-yellow",
  94: "ansi-fg-bright-blue",
  95: "ansi-fg-bright-magenta",
  96: "ansi-fg-bright-cyan",
  97: "ansi-fg-bright-white",
};

const BG_CLASSES: Record<number, string> = {
  40: "ansi-bg-black",
  41: "ansi-bg-red",
  42: "ansi-bg-green",
  43: "ansi-bg-yellow",
  44: "ansi-bg-blue",
  45: "ansi-bg-magenta",
  46: "ansi-bg-cyan",
  47: "ansi-bg-white",
};

function applyCode(state: StyleState, code: number): StyleState {
  if (code === 0) return { bold: false, dim: false, italic: false };
  if (code === 1) return { ...state, bold: true };
  if (code === 2) return { ...state, dim: true };
  if (code === 3) return { ...state, italic: true };
  if (code === 22) return { ...state, bold: false, dim: false };
  if (code === 23) return { ...state, italic: false };
  if (FG_CLASSES[code]) return { ...state, fg: FG_CLASSES[code] };
  if (BG_CLASSES[code]) return { ...state, bg: BG_CLASSES[code] };
  if (code === 39) return { ...state, fg: undefined };
  if (code === 49) return { ...state, bg: undefined };
  return state;
}

function classNames(state: StyleState): string | undefined {
  const parts: string[] = [];
  if (state.bold) parts.push("ansi-bold");
  if (state.dim) parts.push("ansi-dim");
  if (state.italic) parts.push("ansi-italic");
  if (state.fg) parts.push(state.fg);
  if (state.bg) parts.push(state.bg);
  return parts.length ? parts.join(" ") : undefined;
}

function pushSpan(nodes: ReactNode[], text: string, state: StyleState, key: number) {
  if (!text) return;
  const cls = classNames(state);
  nodes.push(cls ? <span key={key} className={cls}>{text}</span> : text);
}

/** Parse ANSI SGR sequences into styled React spans. */
export function parseAnsi(text: string): ReactNode {
  if (!text.includes("\x1b")) return text;

  const nodes: ReactNode[] = [];
  let state: StyleState = { bold: false, dim: false, italic: false };
  let lastIndex = 0;
  let spanKey = 0;
  let match: RegExpExecArray | null;

  ANSI_RE.lastIndex = 0;
  while ((match = ANSI_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      pushSpan(nodes, text.slice(lastIndex, match.index), state, spanKey++);
    }
    const codes = match[1] ? match[1].split(";").map((c) => parseInt(c, 10)) : [0];
    for (const code of codes) {
      if (!Number.isNaN(code)) state = applyCode(state, code);
    }
    lastIndex = ANSI_RE.lastIndex;
  }

  if (lastIndex < text.length) {
    pushSpan(nodes, text.slice(lastIndex), state, spanKey++);
  }

  return nodes.length === 1 ? nodes[0] : <>{nodes}</>;
}
