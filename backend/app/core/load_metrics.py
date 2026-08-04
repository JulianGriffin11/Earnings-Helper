"""Load income-statement metric definitions from config/metrics.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_METRICS_PATH = Path(__file__).resolve().parents[2] / "config" / "metrics.yaml"


@lru_cache
def load_metrics() -> list[dict[str, Any]]:
    """Return the list of metric configs (label, primary, fallbacks, optional derive)."""
    data = yaml.safe_load(_METRICS_PATH.read_text(encoding="utf-8"))
    metrics = data.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise ValueError(f"No metrics found in {_METRICS_PATH}")
    return metrics
