"""Smoke test for debrief agent. Run from backend/:
    uv run python playground/test_debrief.py AMZN              # direct LLM from artifact
    uv run python playground/test_debrief.py META --integration  # full report service pipeline
"""

import argparse
import asyncio
import json
from pathlib import Path

from app.core.settings import get_settings
from app.db.database import get_session_factory
from app.services.debrief_agent import generate_debrief
from app.services.ingest import SECClient
from app.services.report_service import get_or_create_report

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


def print_debrief(report: dict) -> None:
    debrief = report.get("debrief")
    if not debrief:
        print("(no debrief)\n")
        return

    print(f"headline: {debrief['headline']}")
    print(f"assessment: {debrief['overall_assessment']}")
    print(f"debrief_cached: {report.get('debrief_cached')}\n")

    print("key_takeaways:")
    for item in debrief["key_takeaways"]:
        print(f"  - {item}")

    print("\nitems_to_watch:")
    for item in debrief["items_to_watch"]:
        print(f"  - {item}")
    print()


def find_artifact(ticker: str) -> Path | None:
    matches = sorted(ARTIFACTS_DIR.glob(f"{ticker}_*.json"))
    return matches[-1] if matches else None


def run_direct(ticker: str) -> None:
    artifact = find_artifact(ticker)
    if artifact is None:
        print(f"No {ticker} artifact found. Run playground/test_yoy.py {ticker} first.")
        return

    yoy_report = json.loads(artifact.read_text(encoding="utf-8"))
    print(f"=== Direct debrief from {artifact.name} ===\n")
    debrief = generate_debrief(yoy_report)
    print_debrief({"debrief": debrief.model_dump(), "debrief_cached": False})


async def run_integration(ticker: str) -> None:
    settings = get_settings()
    db = get_session_factory()()

    try:
        async with SECClient(settings.sec_user_agent) as client:
            print("=== Run 1 (expect YoY + debrief generation) ===\n")
            report = await get_or_create_report(client, db, ticker)
            if not report:
                return
            print(
                f"{report['ticker']} — cached: {report['cached']}  "
                f"debrief_cached: {report.get('debrief_cached')}\n"
            )
            print_debrief(report)

            print("=== Run 2 (expect cached YoY + cached debrief) ===\n")
            report2 = await get_or_create_report(client, db, ticker)
            if not report2:
                return
            print(
                f"{report2['ticker']} — cached: {report2['cached']}  "
                f"debrief_cached: {report2.get('debrief_cached')}\n"
            )
            print_debrief(report2)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test debrief agent")
    parser.add_argument("ticker", help="Ticker symbol (e.g. META, AMZN)")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run full report service pipeline (SEC + DB + OpenAI)",
    )
    args = parser.parse_args()
    ticker = args.ticker.upper()

    if args.integration:
        asyncio.run(run_integration(ticker))
    else:
        run_direct(ticker)


if __name__ == "__main__":
    main()
