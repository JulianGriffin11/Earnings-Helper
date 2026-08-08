"""SEC HTTP client for data.sec.gov and EDGAR requests."""

import time
from typing import Any

import httpx

# Master SEC Base URLs
BASE_DATA_URL = "https://data.sec.gov"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def get_submissions_url(cik: str) -> str:
    """Returns metadata and filing history URL for a CIK."""
    return f"{BASE_DATA_URL}/submissions/CIK{cik.zfill(10)}.json"


def get_company_facts_url(cik: str) -> str:
    """Returns complete XBRL financial statements dataset URL for a CIK."""
    return f"{BASE_DATA_URL}/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"


def get_company_concept_url(cik: str, concept: str, taxonomy: str = "us-gaap") -> str:
    """Returns single financial concept history URL across reporting periods."""
    return f"{BASE_DATA_URL}/api/xbrl/companyconcept/CIK{cik.zfill(10)}/{taxonomy}/{concept}.json"


FILING_FORMS = frozenset({"10-Q", "10-K"})


class SECClient:
    """HTTP client for SEC EDGAR with automatic rate limiting and caching."""

    def __init__(
        self,
        user_agent: str,
        cache_ttl_seconds: float = 86_400,
        min_request_interval: float = 0.1,
    ) -> None:
        self.user_agent = user_agent
        self.cache_ttl = cache_ttl_seconds
        self.min_interval = min_request_interval

        self.response_cache: dict[str, tuple[float, Any]] = {}
        self.last_request_at = 0.0
        self.http_client: httpx.Client | None = None

    def ensure_http_client(self) -> httpx.Client:
        """Lazy loader: initialize client on demand if not using a context manager."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.Client(
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                timeout=30.0,
                follow_redirects=True,
            )
        return self.http_client

    def fetch_json(self, url: str, use_cache: bool = True) -> Any:
        """Fetches JSON data with rate limiting and cache checking."""
        now = time.monotonic()

        if use_cache and url in self.response_cache:
            cached_at, data = self.response_cache[url]
            if now - cached_at <= self.cache_ttl:
                return data
            del self.response_cache[url]

        elapsed = now - self.last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        client = self.ensure_http_client()
        response = client.get(url)
        response.raise_for_status()

        self.last_request_at = time.monotonic()
        data = response.json()

        if use_cache:
            self.response_cache[url] = (self.last_request_at, data)

        return data

    def fetch_text(self, url: str, use_cache: bool = True) -> str:
        """Fetch a text document (e.g. inline XBRL HTML) with rate limiting."""
        now = time.monotonic()

        if use_cache and url in self.response_cache:
            cached_at, data = self.response_cache[url]
            if now - cached_at <= self.cache_ttl and isinstance(data, str):
                return data
            if url in self.response_cache:
                del self.response_cache[url]

        elapsed = now - self.last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        client = self.ensure_http_client()
        response = client.get(url)
        response.raise_for_status()

        self.last_request_at = time.monotonic()
        data = response.text

        if use_cache:
            self.response_cache[url] = (self.last_request_at, data)

        return data

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self.http_client is not None and not self.http_client.is_closed:
            self.http_client.close()

    def __enter__(self) -> "SECClient":
        self.ensure_http_client()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def latest_filing_date(client: SECClient, cik: str) -> str | None:
    """Latest filingDate among recent 10-Q and 10-K filings."""
    submissions = client.fetch_json(get_submissions_url(cik))
    recent = submissions["filings"]["recent"]
    latest: str | None = None
    for form, filing_date in zip(
        recent["form"], recent["filingDate"], strict=True
    ):
        if form in FILING_FORMS and (latest is None or filing_date > latest):
            latest = filing_date
    return latest
