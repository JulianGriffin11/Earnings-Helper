"""Run all playground tests for a ticker. Run from backend/:
uv run python playground/run_test.py META
uv run python playground/run_test.py AMZN
"""

import subprocess
import sys
from pathlib import Path

PLAYGROUND_DIR = Path(__file__).resolve().parent

STEPS = [
    ("YoY", "test_yoy.py"),
    ("Debrief", "test_debrief.py"),
    ("Report service", "test_report_service.py"),
]


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: uv run python playground/run_test.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1].upper()

    for index, (label, script) in enumerate(STEPS, start=1):
        print(f"\n{'=' * 60}")
        print(f"{index}/{len(STEPS)} {label} — {ticker}")
        print("=" * 60 + "\n")

        result = subprocess.run(
            [sys.executable, str(PLAYGROUND_DIR / script), ticker],
            check=False,
        )
        if result.returncode != 0:
            print(f"\nStopped: {script} failed for {ticker}")
            sys.exit(1)


if __name__ == "__main__":
    main()
