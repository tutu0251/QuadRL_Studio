"""Minimal TOML writer for nested training config dicts."""
from __future__ import annotations

import json
from typing import Any


def _toml_scalar(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                raise TypeError("TOML export does not support arrays of tables in this config")
            items.append(_toml_scalar(item))
        return "[" + ", ".join(items) + "]"
    raise TypeError(f"Unsupported TOML value: {type(value)!r}")


def dump_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    tables: list[tuple[str, dict[str, Any]]] = []

    for key, value in data.items():
        if isinstance(value, dict):
            tables.append((key, value))
        else:
            lines.append(f"{key} = {_toml_scalar(value)}")

    if lines:
        lines.append("")

    for section, table in tables:
        lines.extend(_dump_table(section, table))
    return "\n".join(lines).rstrip() + "\n"


def _dump_table(section: str, table: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    nested: list[tuple[str, dict[str, Any]]] = []

    lines.append(f"[{section}]")
    for key, value in table.items():
        if isinstance(value, dict):
            nested.append((f"{section}.{key}", value))
        else:
            lines.append(f"{key} = {_toml_scalar(value)}")
    lines.append("")

    for path, sub in nested:
        lines.extend(_dump_table(path, sub))
    return lines
