"""Smoke test for YoY metrics. Run from backend/:
    uv run python playground/test_yoy.py

Writes one validation file per run to artifacts/{TICKER}_{date}.json
"""

import asyncio
import json
from datetime import date, datetime
from pathlib import Path

from app.core.settings import get_settings
from app.services.ingest import SECClient
from app.services.resolver import resolve
from app.services.yoy_calculator import compute_yoy

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


def save_artifact(report: dict) -> Path:
    report = {
        **report,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    path = ARTIFACTS_DIR / f"{report['ticker']}_{date.today().isoformat()}.json"
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path


def print_section(title: str, section: dict) -> None:
    print(title)
    if not section["period_end"]:
        print("  (no data)\n")
        return

    print(f"  {section['period_end']} vs {section['prior_period_end']}\n")
    for m in section["metrics"]:
        if m["current"] is None:
            print(f"  {m['label']}: n/a")
            continue
        pct = f"{m['pct_change']:.1f}%" if m["pct_change"] is not None else "n/a"
        tag = m.get("tag") or "?"
        print(
            f"  {m['label']} [{tag}]: ${m['current']:,.0f} "
            f"(prior ${m['prior']:,.0f}, change ${m['dollar_change']:,.0f}, {pct})"
        )
    print()


async def main() -> None:
    settings = get_settings()

    async with SECClient(settings.sec_user_agent) as client:
        company = await resolve(client, "AMZN")
        if not company:
            return

        report = await compute_yoy(client, company)
        artifact_path = save_artifact(report)

        print(f"{report['ticker']} — {report['company']} (CIK {report['cik']})")
        print(f"Saved {artifact_path}\n")

        print_section("quarterly", report["quarterly"])
        print_section("annual", report["annual"])


if __name__ == "__main__":
    asyncio.run(main())
