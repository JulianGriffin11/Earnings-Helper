"""HTTP client for SEC data.sec.gov API."""

import asyncio
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


class SECClient:
    """Async HTTP client for SEC EDGAR with automatic rate limiting and caching."""

    def __init__(
        self,
        user_agent: str,
        cache_ttl_seconds: float = 86_400,
        min_request_interval: float = 0.1,
    ) -> None:
        self.user_agent = user_agent
        self.cache_ttl = cache_ttl_seconds
        self.min_interval = min_request_interval
        
        self._cache: dict[str, tuple[float, Any]] = {}
        self._last_request_at = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy loader: initialize client on demand if not using a context manager."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def fetch_json(self, url: str, use_cache: bool = True) -> Any:
        """Fetches JSON data with rate limiting and cache checking."""
        now = time.monotonic()

        # 1. Return valid cached response if available
        if use_cache and url in self._cache:
            cached_at, data = self._cache[url]
            if now - cached_at <= self.cache_ttl:
                return data
            del self._cache[url]

        # 2. Rate limit check (Max 10 req/sec)
        elapsed = now - self._last_request_at
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)

        # 3. Fetch from SEC API
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        
        self._last_request_at = time.monotonic()
        data = response.json()

        # 4. Save to cache
        if use_cache:
            self._cache[url] = (self._last_request_at, data)

        return data

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "SECClient":
        await self._get_client()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()