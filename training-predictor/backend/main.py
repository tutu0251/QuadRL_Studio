"""Uvicorn entry point: ``uvicorn main:app`` (mirrors the other QuadRL editor backends)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.main import app  # noqa: E402,F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8007)
