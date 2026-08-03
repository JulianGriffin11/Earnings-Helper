"""Unit tests for XBRL extractor using frozen SEC fixtures (no live API)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.extractor import (
    _normalize_observations,
    extract_concept,
)

FIXTURES = Path(__file__).parent / "fixtures"
AMZN_REVENUES = json.loads((FIXTURES / "amzn_revenues.json").read_text())


class FakeSECClient:
    """Minimal stand-in that returns a fixed companyconcept payload."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.urls: list[str] = []

    async def fetch_json(self, url: str, use_cache: bool = True) -> dict:
        self.urls.append(url)
        return self.payload


def test_normalize_filters_forms_and_prefers_latest_filed() -> None:
    observations = [
        {
            "start": "2024-01-01",
            "end": "2024-03-31",
            "val": 100,
            "filed": "2024-04-01",
            "form": "10-Q",
            "fy": 2024,
            "fp": "Q1",
        },
        {
            "start": "2024-01-01",
            "end": "2024-03-31",
            "val": 110,
            "filed": "2024-05-01",
            "form": "10-Q",
            "fy": 2024,
            "fp": "Q1",
        },
        {
            "end": "2024-03-31",
            "val": 999,
            "filed": "2024-06-01",
            "form": "10-Q",
            "fy": 2024,
            "fp": "Q1",
        },
        {
            "start": "2023-01-01",
            "end": "2023-12-31",
            "val": 500,
            "filed": "2024-02-01",
            "form": "8-K",
            "fy": 2023,
            "fp": "FY",
        },
        {
            "start": "2023-01-01",
            "end": "2023-12-31",
            "val": 450,
            "filed": "2024-02-01",
            "form": "10-K",
            "fy": 2023,
            "fp": "FY",
        },
    ]

    facts = _normalize_observations(observations, ("10-Q", "10-K"))

    assert len(facts) == 2
    by_end = {f.end: f for f in facts}
    # Latest filed duration wins over older duration and later instant.
    assert by_end["2024-03-31"].val == 110
    assert by_end["2024-03-31"].start == "2024-01-01"
    # 8-K dropped; 10-K kept.
    assert by_end["2023-12-31"].val == 450
    assert by_end["2023-12-31"].form == "10-K"


@pytest.mark.asyncio
async def test_extract_concept_from_frozen_amzn_fixture() -> None:
    client = FakeSECClient(AMZN_REVENUES)

    facts = await extract_concept(
        client,
        "0001018724",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
    )

    assert client.urls
    assert "companyconcept" in client.urls[0]
    assert facts
    assert all(f.form in {"10-Q", "10-K"} for f in facts)
    assert all(f.end and f.filed and f.val is not None for f in facts)
    # Chronological by period end
    assert [f.end for f in facts] == sorted(f.end for f in facts)

    latest = facts[-1]
    assert latest.form in {"10-Q", "10-K"}
    assert latest.val > 0
