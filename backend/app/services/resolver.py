"""Resolve ticker symbols and company names to SEC CIK.

Responsibilities (Phase 1):
- Load company_tickers.json from SEC
- Search by ticker (AMZN) or partial name (Amazon)
- Return ticker, name, cik
"""

from app.services.ingest import COMPANY_TICKERS_URL, SECClient


async def resolve(client: SECClient, query: str) -> dict | None:
    """Look up a company by ticker or partial name.

    Returns {"ticker", "name", "cik"} or None if nothing matches.
    """
    tickers = await client.fetch_json(COMPANY_TICKERS_URL)
    cleaned = query.strip()
    if not cleaned:
        print("No company found")
        return None

    # Exact ticker match first
    for entry in tickers.values():
        if entry["ticker"].upper() == cleaned.upper():
            return {
                "ticker": entry["ticker"].upper(),
                "name": entry["title"],
                "cik": str(entry["cik_str"]).zfill(10),
            }

    # Then partial company name match
    needle = cleaned.casefold()
    for entry in tickers.values():
        if needle in entry["title"].casefold():
            return {
                "ticker": entry["ticker"].upper(),
                "name": entry["title"],
                "cik": str(entry["cik_str"]).zfill(10),
            }

    print("No company found")
    return None
