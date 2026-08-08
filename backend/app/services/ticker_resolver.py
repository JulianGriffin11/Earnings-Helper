"""Map ticker symbols and company names to SEC CIK."""

from app.services.sec_client import COMPANY_TICKERS_URL, SECClient


def entry_to_result(entry: dict) -> dict[str, str]:
    return {
        "ticker": entry["ticker"].upper(),
        "name": entry["title"],
        "cik": str(entry["cik_str"]).zfill(10),
    }


def search(client: SECClient, query: str, *, limit: int = 10) -> list[dict[str, str]]:
    """Return up to `limit` companies matching ticker or partial name."""
    cleaned = query.strip()
    if not cleaned:
        return []

    tickers = client.fetch_json(COMPANY_TICKERS_URL)
    results: list[dict[str, str]] = []
    seen_ciks: set[str] = set()

    for entry in tickers.values():
        if entry["ticker"].upper() == cleaned.upper():
            result = entry_to_result(entry)
            if result["cik"] not in seen_ciks:
                results.append(result)
                seen_ciks.add(result["cik"])

    needle = cleaned.casefold()
    for entry in tickers.values():
        if needle in entry["title"].casefold():
            result = entry_to_result(entry)
            if result["cik"] not in seen_ciks:
                results.append(result)
                seen_ciks.add(result["cik"])
            if len(results) >= limit:
                break

    return results[:limit]


def resolve(client: SECClient, query: str) -> dict | None:
    """Look up a company by ticker or partial name.

    Returns {"ticker", "name", "cik"} or None if nothing matches.
    """
    cleaned = query.strip()
    if not cleaned:
        print("No company found")
        return None

    results = search(client, cleaned, limit=1)
    if not results:
        print("No company found")
        return None
    return results[0]
