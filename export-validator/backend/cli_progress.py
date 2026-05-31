"""Live CLI progress lines for validate_*_runtime.sh."""
from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import datetime

LogFn = Callable[[str], None]


def cli_log(label: str = "runtime") -> LogFn:
    prefix = f"[{label}]"

    def log(message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"{ts} {prefix} {message}", flush=True)

    return log


def log_stage(log: LogFn, title: str) -> None:
    log(f"=== {title} ===")
