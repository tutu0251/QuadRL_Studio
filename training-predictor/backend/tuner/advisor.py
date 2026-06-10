"""Claude-in-the-loop advisor (two interchangeable backends).

Every N trials the study calls the advisor with the live Optuna study and search space. The
advisor summarizes ``study.trials_dataframe()`` and asks Claude for a structured decision —
adjust reward weights, re-center the search space, or stop. The study then applies it.

Backends (selected by ``QUADRL_ADVISOR_BACKEND`` = auto | api | claude_cli | off):
- **api**: the Anthropic developer API via the ``anthropic`` SDK. Needs ``ANTHROPIC_API_KEY``
  (or an API-scoped ``ant auth login`` profile). Uses ``claude-opus-4-8``, adaptive thinking,
  and structured JSON output (``output_config.format``).
- **claude_cli**: shells out to the local ``claude`` CLI in headless print mode
  (``claude -p … --output-format json``). This is authenticated by your **Claude Code
  subscription (Max/Pro)** login, so it needs no API key. Structured output isn't enforced by
  the CLI, so the decision JSON is requested in the prompt and parsed from the result.
- **auto** (default): api if an API key is present, else claude_cli if the binary is found,
  else disabled (study runs as pure Optuna).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Optional

LogFn = Callable[[str, str], None]
MODEL = "claude-opus-4-8"

# Condensed from training/quadrl_env/rewards.py so Claude knows what each weight controls.
REWARD_SEMANTICS = """\
Reward-term semantics (quadruped PPO locomotion). Every term returns a value in [0,1]:
- Reward terms (positive weight, ADD reward): alive (=1 while not fallen), upright (1 when
  level, sigma=tilt tolerance), height (matches target body height, sigma), posture (joints
  near rest pose, sigma), contact (>=min feet down, sigma), forward/lateral/yaw_tracking
  (match commanded velocity, sigma), diagonal_balance, air_time, foot_clearance.
- Penalty terms (negative weight, SUBTRACT, bounded by |weight|): angular_velocity,
  linear_velocity, z_velocity, joint_velocity, action_velocity/action_rate/smoothness
  (penalize jerky actions), posture_penalty/target_posture, contact_balance, contact_switch
  (foot chatter), target_like, stumble, slip, zmp. Smaller sigma = sharper penalty.
A smaller sigma makes a term more sensitive (steeper gradient near the optimum).
Standing/balance tasks lean on alive+upright+height+posture and the smoothness penalties;
locomotion additionally needs the *_tracking rewards enabled and weighted up."""

SYSTEM_PROMPT = f"""You are an expert reinforcement-learning tuning advisor embedded in an \
Optuna study that is optimizing PPO training of a quadruped robot. Optuna samples the numeric \
trials; you are consulted every few trials to steer the search.

{REWARD_SEMANTICS}

You will receive a JSON summary of completed trials (objective = mean episode reward, higher \
is better), the parameters explored, and the CURRENT search-space bounds. Decide ONE action:
- "continue": the search is healthy; change nothing.
- "adjust_reward_weights": recommend better reward/penalty weight magnitudes. Provide \
  reward_weight_overrides (term id -> new magnitude, always >= 0; sign is handled for you). \
  This re-centers each weight's search bounds around your value. Optionally also set \
  reward_param_overrides (e.g. a term's sigma).
- "recenter_search_space": narrow or shift bounds for specific parameters via \
  search_space_overrides (names like 'hp.learning_rate', 'rw.upright', 'rp.upright.sigma'; \
  set low/high, log scale, or pin with 'fix').
- "stop": objective has plateaued or is regressing and further trials aren't worthwhile; set stop=true.

Only include overrides relevant to your action; leave the others as empty arrays. Always give \
a concise, concrete rationale grounded in the trial data. Be conservative: don't pin or \
collapse bounds unless the data clearly supports it."""

# For the CLI backend (no schema enforcement): describe the exact JSON contract in the prompt.
DECISION_INSTRUCTIONS = """\
Respond with ONLY a single JSON object (no prose, no markdown fences) of exactly this shape:
{
  "action": "continue" | "adjust_reward_weights" | "recenter_search_space" | "stop",
  "stop": <bool>,
  "rationale": <string>,
  "reward_weight_overrides": [ {"id": <term id>, "value": <number >= 0>} ],
  "reward_param_overrides":  [ {"id": <term id>, "param": <string>, "value": <number>} ],
  "search_space_overrides":  [ {"name": <param name>, "low": <number|null>, "high": <number|null>, "log": <bool|null>, "fix": <number|null>} ]
}
Include only the overrides relevant to your chosen action; use empty arrays otherwise."""


def _nullable(*types: str) -> dict:
    return {"type": [*types, "null"]}


DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "action", "stop", "rationale",
        "reward_weight_overrides", "reward_param_overrides", "search_space_overrides",
    ],
    "properties": {
        "action": {
            "type": "string",
            "enum": ["continue", "adjust_reward_weights", "recenter_search_space", "stop"],
        },
        "stop": {"type": "boolean"},
        "rationale": {"type": "string"},
        "reward_weight_overrides": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", "value"],
                "properties": {"id": {"type": "string"}, "value": {"type": "number"}},
            },
        },
        "reward_param_overrides": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", "param", "value"],
                "properties": {
                    "id": {"type": "string"}, "param": {"type": "string"},
                    "value": {"type": "number"},
                },
            },
        },
        "search_space_overrides": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["name", "low", "high", "log", "fix"],
                "properties": {
                    "name": {"type": "string"},
                    "low": _nullable("number"),
                    "high": _nullable("number"),
                    "log": _nullable("boolean"),
                    "fix": _nullable("number"),
                },
            },
        },
    },
}


def summarize(study, space, *, top: int = 6, bottom: int = 3) -> dict[str, Any]:
    """Build a compact JSON-able summary of the study for the model."""
    try:
        import optuna
        completed = [t for t in study.trials
                     if t.state == optuna.trial.TrialState.COMPLETE and t.value is not None]
    except Exception:  # pragma: no cover - optuna always present at runtime
        completed = [t for t in study.trials if getattr(t, "value", None) is not None]

    ranked = sorted(completed, key=lambda t: t.value, reverse=True)

    def row(t):
        return {"number": t.number, "value": round(float(t.value), 5),
                "params": {k: _round(v) for k, v in t.params.items()}}

    explored: dict[str, dict[str, float]] = {}
    for t in completed:
        for k, v in t.params.items():
            if isinstance(v, (int, float)):
                rng = explored.setdefault(k, {"min": v, "max": v})
                rng["min"] = min(rng["min"], v)
                rng["max"] = max(rng["max"], v)

    best = ranked[0] if ranked else None
    return {
        "n_completed": len(completed),
        "best": ({"number": best.number, "value": round(float(best.value), 5),
                  "params": {k: _round(v) for k, v in best.params.items()}} if best else None),
        "top_trials": [row(t) for t in ranked[:top]],
        "worst_trials": [row(t) for t in ranked[-bottom:]] if len(ranked) > top else [],
        "explored_ranges": {k: {"min": _round(v["min"]), "max": _round(v["max"])}
                            for k, v in explored.items()},
        "current_search_space": space.snapshot(),
    }


def _round(v):
    if isinstance(v, float):
        return round(v, 6)
    return v


def _user_prompt(summary: dict[str, Any], *, include_instructions: bool) -> str:
    parts = ["Review this study and return your decision.\n",
             json.dumps(summary, indent=2)]
    if include_instructions:
        parts.append("\n\n" + DECISION_INSTRUCTIONS)
    return "".join(parts)


def _extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of free-form model text (strip fences, take the outermost braces)."""
    t = text.strip()
    if t.startswith("```"):
        t = t[3:]
        if t[:4].lower() == "json":
            t = t[4:]
        t = t.strip().rstrip("`").strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        return json.loads(t[start:end + 1])
    return json.loads(t)


def find_claude_cli() -> Optional[str]:
    """Locate the headless ``claude`` binary (Max/Pro subscription auth).

    Checks, in order: ``QUADRL_CLAUDE_CLI`` / ``CLAUDE_CODE_EXECPATH`` overrides, the
    PATH, and finally common install locations — the per-user install and the
    VS Code / Cursor extension's bundled native binary. The last fallback matters
    because the API is often launched as a service whose PATH omits ``claude``,
    which would otherwise disable the advisor even though the CLI is installed.
    """
    import glob

    env = os.environ.get("QUADRL_CLAUDE_CLI")
    if env and os.path.exists(env):
        return env
    execpath = os.environ.get("CLAUDE_CODE_EXECPATH")
    if execpath and os.path.exists(execpath):
        return execpath
    on_path = shutil.which("claude")
    if on_path:
        return on_path

    candidates: list[str] = [os.path.expanduser("~/.claude/local/claude")]
    for pat in (
        "~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude",
        "~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude",
        "~/.cursor-server/extensions/anthropic.claude-code-*/resources/native-binary/claude",
    ):
        candidates.extend(sorted(glob.glob(os.path.expanduser(pat)), reverse=True))
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


# --------------------------------------------------------------------------- backends


class _BaseAdvisor:
    backend = "disabled"
    available = False
    reason: Optional[str] = None

    def __init__(self, *, log: LogFn = lambda l, m: None):
        self.log = log

    def advise(self, study, space) -> Optional[dict[str, Any]]:  # pragma: no cover - overridden
        return None

    def describe(self) -> str:
        if self.available:
            return f"{self.backend} ({getattr(self, 'model', '')})".strip()
        return f"DISABLED ({self.reason})"


class DisabledAdvisor(_BaseAdvisor):
    def __init__(self, reason: str, *, log: LogFn = lambda l, m: None):
        super().__init__(log=log)
        self.reason = reason

    def advise(self, study, space):
        self.log("warn", f"Advisor disabled ({self.reason}); running pure Optuna.")
        return None


class ClaudeApiAdvisor(_BaseAdvisor):
    backend = "api"

    def __init__(self, *, model: str = MODEL, log: LogFn = lambda l, m: None):
        super().__init__(log=log)
        self.model = model
        self._client = None
        if not os.environ.get("ANTHROPIC_API_KEY"):
            self.reason = "ANTHROPIC_API_KEY not set"
            return
        try:
            import anthropic
            self._client = anthropic.Anthropic()
            self.available = True
        except Exception as exc:  # pragma: no cover - import/env dependent
            self.reason = f"anthropic SDK unavailable: {exc}"

    def advise(self, study, space) -> Optional[dict[str, Any]]:
        if not self.available:
            self.log("warn", f"Advisor disabled ({self.reason}); running pure Optuna.")
            return None
        summary = summarize(study, space)
        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=8000,
                thinking={"type": "adaptive"},
                output_config={
                    "effort": "high",
                    "format": {"type": "json_schema", "schema": DECISION_SCHEMA},
                },
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _user_prompt(summary, include_instructions=False)}],
            )
        except Exception as exc:
            self.log("error", f"Advisor API call failed: {exc}")
            return None
        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), None)
        if not text:
            self.log("error", "Advisor returned no text block.")
            return None
        return _safe_parse(text, self.log)


class ClaudeCliAdvisor(_BaseAdvisor):
    backend = "claude_cli"

    def __init__(self, *, model: str = MODEL, log: LogFn = lambda l, m: None, timeout: float = 300.0):
        super().__init__(log=log)
        self.model = model
        self.timeout = timeout
        self._cli = find_claude_cli()
        if self._cli:
            self.available = True
        else:
            self.reason = "claude CLI not found (set QUADRL_CLAUDE_CLI)"

    def advise(self, study, space) -> Optional[dict[str, Any]]:
        if not self.available:
            self.log("warn", f"Advisor disabled ({self.reason}); running pure Optuna.")
            return None
        summary = summarize(study, space)
        cmd = [
            self._cli, "-p", _user_prompt(summary, include_instructions=True),
            "--output-format", "json", "--model", self.model,
            "--system-prompt", SYSTEM_PROMPT,
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout,
                cwd=tempfile.gettempdir())
        except Exception as exc:
            self.log("error", f"Advisor CLI call failed: {exc}")
            return None
        if proc.returncode != 0:
            self.log("error", f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[:300]}")
            return None
        # The CLI prints a JSON envelope; the model's answer is in `result`.
        result_text = proc.stdout
        try:
            env = json.loads(proc.stdout)
            if isinstance(env, dict):
                if env.get("is_error"):
                    self.log("error", f"claude CLI reported error: {env.get('result')}")
                    return None
                result_text = env.get("result", proc.stdout)
        except json.JSONDecodeError:
            pass  # not an envelope — treat stdout as the raw answer
        return _safe_parse(result_text, self.log)


def _safe_parse(text: str, log: LogFn) -> Optional[dict[str, Any]]:
    try:
        return _extract_json(text)
    except json.JSONDecodeError as exc:
        log("error", f"Advisor returned unparseable JSON: {exc}")
        return None


def make_advisor(*, log: LogFn = lambda l, m: None, backend: Optional[str] = None) -> _BaseAdvisor:
    """Construct the advisor for the configured/auto-detected backend."""
    backend = (backend or os.environ.get("QUADRL_ADVISOR_BACKEND", "auto")).lower()
    if backend in ("off", "none", "disabled"):
        return DisabledAdvisor("backend set to off", log=log)
    if backend == "api":
        return ClaudeApiAdvisor(log=log)
    if backend in ("claude_cli", "cli"):
        return ClaudeCliAdvisor(log=log)
    # auto
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeApiAdvisor(log=log)
    if find_claude_cli():
        return ClaudeCliAdvisor(log=log)
    return DisabledAdvisor("no ANTHROPIC_API_KEY and no claude CLI", log=log)


# Backwards-compatible alias (tests / external callers).
ClaudeAdvisor = ClaudeApiAdvisor
