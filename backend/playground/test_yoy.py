"""Generate YoY artifact JSON for diagnosis. Run from backend/:
    uv run python playground/test_yoy.py META
    uv run python playground/test_yoy.py AMZN --no-debug
"""

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

from app.core.load_metrics import load_metrics
from app.core.settings import get_settings
from app.services.ingest import SECClient
from app.services.resolver import resolve
from app.services.yoy_calculator import (
    REVENUE_LABEL,
    fetch_tag_facts,
    pick_period_ends,
    compute_yoy,
)

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


def latest_form_end(facts: list, form: str) -> str | None:
    ends = [f.end for f in facts if f.form == form]
    return max(ends) if ends else None


def period_pair_dict(ends: tuple[str, str] | None) -> dict[str, str | None]:
    if ends is None:
        return {"period_end": None, "prior_period_end": None}
    return {"period_end": ends[0], "prior_period_end": ends[1]}


async def build_revenue_tag_debug(
    client: SECClient,
    cik: str,
    tags: list[str],
) -> list[dict[str, Any]]:
    cache: dict[str, list] = {}
    rows: list[dict[str, Any]] = []

    for tag in tags:
        facts = await fetch_tag_facts(client, cik, tag, cache)
        quarterly = pick_period_ends(facts, "10-Q")
        annual = pick_period_ends(facts, "10-K")
        rows.append(
            {
                "tag": tag,
                "fact_count": len(facts),
                "latest_10q_end": latest_form_end(facts, "10-Q"),
                "latest_10k_end": latest_form_end(facts, "10-K"),
                "quarterly_yoy": period_pair_dict(quarterly),
                "annual_yoy": period_pair_dict(annual),
            }
        )

    return rows


def print_summary(ticker: str, yoy: dict[str, Any]) -> None:
    print(f"{ticker} — {yoy['company']} (CIK {yoy['cik']})\n")

    for section_name in ("quarterly", "annual"):
        section = yoy[section_name]
        print(section_name)
        if not section["period_end"]:
            print("  (no data)\n")
            continue
        print(f"  {section['period_end']} vs {section['prior_period_end']}\n")
        for metric in section["metrics"]:
            if metric["current"] is None:
                print(f"  {metric['label']}: n/a (tag: {metric.get('tag')})")
                continue
            pct = (
                f"{metric['pct_change']:.1f}%"
                if metric["pct_change"] is not None
                else "n/a"
            )
            print(
                f"  {metric['label']}: ${metric['current']:,.0f} "
                f"(prior ${metric['prior']:,.0f}, {pct}) "
                f"[{metric.get('tag')}]"
            )
        print()


def print_debug(debug: list[dict[str, Any]]) -> None:
    print("=== Revenue tag debug ===\n")
    for row in debug:
        print(f"  {row['tag']} ({row['fact_count']} facts)")
        print(f"    latest 10-Q end: {row['latest_10q_end']}")
        print(f"    latest 10-K end: {row['latest_10k_end']}")
        q = row["quarterly_yoy"]
        a = row["annual_yoy"]
        print(
            f"    quarterly YoY pair: {q['period_end']} vs {q['prior_period_end']}"
        )
        print(f"    annual YoY pair: {a['period_end']} vs {a['prior_period_end']}")
        print()


async def run(ticker: str, *, include_debug: bool = True) -> None:
    settings = get_settings()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    async with SECClient(settings.sec_user_agent) as client:
        company = await resolve(client, ticker)
        if not company:
            return

        yoy = await compute_yoy(client, company)

        debug: list[dict[str, Any]] | None = None
        if include_debug:
            revenue = next(m for m in load_metrics() if m["label"] == REVENUE_LABEL)
            revenue_tags = [revenue["primary"], *revenue.get("fallbacks", [])]
            debug = await build_revenue_tag_debug(client, company["cik"], revenue_tags)

        artifact: dict[str, Any] = {
            "generated_at": date.today().isoformat(),
            **yoy,
        }
        if debug is not None:
            artifact["debug"] = {"revenue_tags": debug}

        out_path = ARTIFACTS_DIR / f"{company['ticker']}_{date.today().isoformat()}.json"
        out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

        print_summary(company["ticker"], yoy)
        if debug is not None:
            print_debug(debug)
        print(f"Wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate YoY artifact for a ticker")
    parser.add_argument("ticker", help="Ticker symbol (e.g. META, AMZN)")
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Omit revenue tag debug block from artifact output",
    )
    args = parser.parse_args()
    asyncio.run(run(args.ticker.upper(), include_debug=not args.no_debug))


if __name__ == "__main__":
    main()
