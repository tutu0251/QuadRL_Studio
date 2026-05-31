"""Default checkpoint, best-model, and export settings."""
from __future__ import annotations

from domain.models import BestModelConfig, CheckpointConfig, ExportFormatConfig

DEFAULT_CHECKPOINT = CheckpointConfig()
DEFAULT_BEST_MODEL = BestModelConfig()
DEFAULT_EXPORT_FORMAT = ExportFormatConfig()
