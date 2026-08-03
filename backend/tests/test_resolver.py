"""Unit tests for company resolver using a frozen ticker fixture (no live API)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.ingest import COMPANY_TICKERS_URL
from app.services.resolver import resolve

FIXTURES = Path(__file__).parent / "fixtures"
TICKERS = json.loads((FIXTURES / "company_tickers_sample.json").read_text())


class FakeSECClient:
    async def fetch_json(self, url: str, use_cache: bool = True) -> dict:
        assert url == COMPANY_TICKERS_URL
        return TICKERS


@pytest.mark.asyncio
async def test_resolve_by_ticker() -> None:
    result = await resolve(FakeSECClient(), "amzn")
    assert result == {
        "ticker": "AMZN",
        "name": "AMAZON COM INC",
        "cik": "0001018724",
    }


@pytest.mark.asyncio
async def test_resolve_by_partial_name() -> None:
    result = await resolve(FakeSECClient(), "Amazon")
    assert result is not None
    assert result["ticker"] == "AMZN"
    assert result["cik"] == "0001018724"


@pytest.mark.asyncio
async def test_resolve_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    result = await resolve(FakeSECClient(), "NOTAREALCO")
    assert result is None
    assert "No company found" in capsys.readouterr().out
