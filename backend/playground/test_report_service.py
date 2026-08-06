"""Smoke test for report service cache. Run from backend/:
    uv run python playground/test_report_service.py
"""

import asyncio

from app.core.settings import get_settings
from app.db.database import get_session_factory
from app.db.models import Company, Report
from app.services.ingest import SECClient
from app.services.report_service import get_or_create_report


def print_summary(report: dict) -> None:
    print(f"{report['ticker']} — {report['company']} (CIK {report['cik']})")
    print(
        f"filing_date: {report['filing_date']}  cached: {report['cached']}  "
        f"debrief_cached: {report.get('debrief_cached')}\n"
    )

    for section_name in ("quarterly", "annual"):
        section = report[section_name]
        print(section_name)
        if not section["period_end"]:
            print("  (no data)\n")
            continue
        print(f"  {section['period_end']} vs {section['prior_period_end']}\n")
        for m in section["metrics"]:
            if m["current"] is None:
                print(f"  {m['label']}: n/a")
                continue
            pct = (
                f"{m['pct_change']:.1f}%"
                if m["pct_change"] is not None
                else "n/a"
            )
            print(
                f"  {m['label']}: ${m['current']:,.0f} "
                f"(prior ${m['prior']:,.0f}, {pct})"
            )
        print()


async def main() -> None:
    settings = get_settings()
    db = get_session_factory()()

    try:
        async with SECClient(settings.sec_user_agent) as client:
            print("=== Run 1 (expect cache miss) ===\n")
            report = await get_or_create_report(client, db, "AMZN")
            if not report:
                return
            print_summary(report)

            print("=== Run 2 (expect cache hit) ===\n")
            report2 = await get_or_create_report(client, db, "AMZN")
            if not report2:
                return
            print_summary(report2)

            if report2.get("debrief"):
                print("debrief headline:", report2["debrief"]["headline"])

        companies = db.query(Company).count()
        reports = db.query(Report).count()
        print(f"DB rows — companies: {companies}, reports: {reports}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
