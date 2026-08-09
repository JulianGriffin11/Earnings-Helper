"""Batch YoY smoke test for multiple tickers. Run from backend/:
    uv run python playground/test_yoy_batch.py
    uv run python playground/test_yoy_batch.py AAPL WMT TSLA
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PLAYGROUND_DIR = Path(__file__).resolve().parent
DEFAULT_TICKERS = ("AAPL", "MSFT", "META", "AMZN", "NVDA", "GOOGL", "WMT", "TSLA")
METRIC_LABELS = ("Revenue", "Operating Expenses", "Gross Profit", "Net Income")


def main() -> None:
    tickers = tuple(arg.upper() for arg in sys.argv[1:]) or DEFAULT_TICKERS
    failed: list[str] = []

    for ticker in tickers:
        print(f"\n{'=' * 60}")
        print(ticker)
        print("=" * 60)

        result = subprocess.run(
            [sys.executable, str(PLAYGROUND_DIR / "test_yoy.py"), ticker, "--no-debug"],
            check=False,
        )
        if result.returncode != 0:
            failed.append(f"{ticker}: script error")

    if failed:
        print("\nFailures:")
        for item in failed:
            print(f"  - {item}")
        sys.exit(1)

    print(f"\nRan {len(tickers)} tickers. Check output above for any n/a metrics.")


if __name__ == "__main__":
    main()
