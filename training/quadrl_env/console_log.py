"""Pretty console logging for QuadRL training scripts.

Centralizes formatting so training launcher + Gazebo/ROS backend output look consistent.
Falls back to plain printing if rich isn't available or output isn't a TTY.
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass


_TAG_RE = re.compile(r"^\[(?P<tag>[^\]]+)\]\s*")


def _now_stamp() -> str:
    # Match the user's preferred format, e.g. "3:24:40 AM"
    stamp = time.strftime("%I:%M:%S %p")
    return stamp[1:] if stamp.startswith("0") else stamp


def _strip_leading_tags(text: str) -> tuple[list[str], str]:
    tags: list[str] = []
    rest = text.strip()
    while True:
        m = _TAG_RE.match(rest)
        if not m:
            break
        tags.append(m.group("tag"))
        rest = rest[m.end() :].lstrip()
    return tags, rest


def _level_from_tags(tags: list[str]) -> str:
    for t in tags:
        low = t.strip().lower()
        if low in ("info", "warn", "warning", "error", "debug"):
            return "warn" if low == "warning" else low
    return "info"


def _component_from_tags(tags: list[str]) -> str | None:
    # Common components in this repo are "train" and "gazebo"
    for t in tags:
        low = t.strip().lower()
        if low in ("train", "gazebo", "sim", "ros"):
            return low
    return None


def _should_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("QUADRL_PLAIN_LOGS", "").strip().lower() in ("1", "true", "yes", "on"):
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


@dataclass(frozen=True)
class LogRecord:
    stamp: str
    level: str
    component: str | None
    message: str


def _parse_record(msg: str, *, default_component: str | None = None) -> LogRecord:
    tags, rest = _strip_leading_tags(msg)
    level = _level_from_tags(tags)
    component = _component_from_tags(tags) or default_component
    return LogRecord(stamp=_now_stamp(), level=level, component=component, message=rest or msg.strip())


def _plain_line(rec: LogRecord) -> str:
    level = rec.level
    comp = rec.component
    parts = [f"[{rec.stamp}]", f"[{level}]"]
    if comp:
        parts.append(f"[{comp}]")
    parts.append(rec.message)
    return " ".join(parts)


def _rich_print(rec: LogRecord) -> None:
    from rich.console import Console
    from rich.text import Text

    console = Console(highlight=False, soft_wrap=True)
    t = Text()

    # Timestamp
    t.append(f"[{rec.stamp}] ", style="dim")

    # Level pill
    level = rec.level.lower()
    level_style = {
        "info": "bold cyan",
        "debug": "dim",
        "warn": "bold yellow",
        "error": "bold red",
    }.get(level, "bold cyan")
    t.append(f"[{level}]", style=level_style)
    t.append(" ")

    # Component pill
    if rec.component:
        comp_style = {"train": "bold green", "gazebo": "bold magenta", "ros": "bold magenta"}.get(
            rec.component, "bold green"
        )
        t.append(f"[{rec.component}]", style=comp_style)
        t.append(" ")

    # Message body
    t.append(rec.message)
    console.print(t)


def log(msg: str, *, default_component: str | None = None) -> None:
    """Log a single line with consistent formatting."""
    rec = _parse_record(msg, default_component=default_component)
    if _should_color():
        try:
            _rich_print(rec)
            return
        except Exception:
            # If rich is misconfigured, fall back safely.
            pass
    print(_plain_line(rec), flush=True)

