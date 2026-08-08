"""Progress callback utilities for report pipeline logging."""

from __future__ import annotations

import time
from collections.abc import Callable

ProgressCallback = Callable[[str], None]


class ProgressLogger:
    """Print progress messages with elapsed time — for playground/CLI use."""

    def __init__(self, *, prefix: str = "") -> None:
        self._start = time.monotonic()
        self._prefix = f"{prefix} " if prefix else ""

    def __call__(self, message: str) -> None:
        elapsed = time.monotonic() - self._start
        print(f"{self._prefix}[{elapsed:5.1f}s] {message}", flush=True)
