"""HTTP client for SEC data.sec.gov API.

Responsibilities (Phase 1):
- Set User-Agent header on every request
- In-memory cache for SEC responses
- Respect ~10 requests/second rate limit
"""
