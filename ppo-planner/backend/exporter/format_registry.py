"""Export format metadata and filename helpers."""
from __future__ import annotations

from domain.models import ExportConfigFormat

FORMAT_EXTENSIONS: dict[ExportConfigFormat, str] = {
    ExportConfigFormat.YAML: ".yaml",
    ExportConfigFormat.JSON: ".json",
    ExportConfigFormat.JSON_MIN: ".min.json",
    ExportConfigFormat.TOML: ".toml",
}

JSON_LIKE: frozenset[ExportConfigFormat] = frozenset(
    {ExportConfigFormat.JSON, ExportConfigFormat.JSON_MIN}
)


def config_filename(project_name: str, fmt: ExportConfigFormat, *, prefix: str = "ppo_") -> str:
    ext = FORMAT_EXTENSIONS[fmt]
    return f"{prefix}{project_name}_config{ext}"
