"""Smoke test for debrief agent. Run from backend/:
    uv run python playground/test_debrief.py              # direct LLM from artifact
    uv run python playground/test_debrief.py --integration  # full report service pipeline
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


def run_direct() -> None:
    artifact = ARTIFACTS_DIR / "AMZN_2026-08-04.json"
    if not artifact.exists():
        matches = sorted(ARTIFACTS_DIR.glob("AMZN_*.json"))
        artifact = matches[-1] if matches else None

    if artifact is None:
        print("No AMZN artifact found. Run playground/test_yoy.py first.")
        return

    yoy_report = json.loads(artifact.read_text(encoding="utf-8"))
    print(f"=== Direct debrief from {artifact.name} ===\n")
    debrief = generate_debrief(yoy_report)
    print_debrief({"debrief": debrief.model_dump(), "debrief_cached": False})


async def run_integration() -> None:
    settings = get_settings()
    db = get_session_factory()()

    try:
        async with SECClient(settings.sec_user_agent) as client:
            print("=== Run 1 (expect YoY + debrief generation) ===\n")
            report = await get_or_create_report(client, db, "AMZN")
            if not report:
                return
            print(
                f"{report['ticker']} — cached: {report['cached']}  "
                f"debrief_cached: {report.get('debrief_cached')}\n"
            )
            print_debrief(report)

            print("=== Run 2 (expect cached YoY + cached debrief) ===\n")
            report2 = await get_or_create_report(client, db, "AMZN")
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run full report service pipeline (SEC + DB + OpenAI)",
    )
    args = parser.parse_args()

    if args.integration:
        asyncio.run(run_integration())
    else:
        run_direct()


if __name__ == "__main__":
    main()
