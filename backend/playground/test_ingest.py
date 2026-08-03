"""Smoke test for SEC ingest + resolver + extractor. Run from backend/:
    uv run python playground/test_ingest.py
"""

import asyncio

from app.core.settings import get_settings
from app.services.extractor import extract_concept
from app.services.ingest import SECClient, get_company_facts_url, get_submissions_url
from app.services.resolver import resolve


async def main() -> None:
    settings = get_settings()

    async with SECClient(settings.sec_user_agent) as client:
        by_ticker = await resolve(client, "AMZN")
        by_name = await resolve(client, "Amazon")
        if not by_ticker or not by_name:
            return

        print("resolver")
        print(f"  AMZN → {by_ticker['ticker']} | {by_ticker['name']} | CIK {by_ticker['cik']}")
        print(f"  Amazon → {by_name['ticker']} | {by_name['name']} | CIK {by_name['cik']}\n")

        cik = by_ticker["cik"]

        # --- submissions ---
        submissions = await client.fetch_json(get_submissions_url(cik))
        recent = submissions["filings"]["recent"]
        print("submissions")
        print(f"  name: {submissions['name']}")
        print(f"  recent filings: {len(recent['form'])}")
        print(f"  latest: {recent['form'][0]} filed {recent['filingDate'][0]}\n")

        # --- company facts ---
        facts = await client.fetch_json(get_company_facts_url(cik))
        gaap_tags = facts["facts"].get("us-gaap", {})
        print("company_facts")
        print(f"  entity: {facts['entityName']}")
        print(f"  us-gaap tags: {len(gaap_tags)}\n")

        # --- extractor (normalized company concept) ---
        concept = "RevenueFromContractWithCustomerExcludingAssessedTax"
        normalized = await extract_concept(client, cik, concept)
        latest = normalized[-1] if normalized else None
        print("extractor")
        print(f"  concept: {concept}")
        print(f"  normalized facts: {len(normalized)}")
        if latest:
            print(
                f"  latest: ${latest.val:,.0f} "
                f"({latest.form} {latest.fy} {latest.fp}, end={latest.end})"
            )


if __name__ == "__main__":
    asyncio.run(main())
