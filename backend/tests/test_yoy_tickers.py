"""Live SEC integration tests for multi-company YoY coverage.

Run: cd backend && uv run pytest tests/test_yoy_tickers.py -v
Skip network: uv run pytest tests/ -v -m "not integration"
"""

from __future__ import annotations

import pytest

from app.core.settings import get_settings
from app.services.sec_client import SECClient
from app.services.ticker_resolver import resolve
from app.services.yoy_calculator import REVENUE_LABEL, compute_yoy

METRIC_LABELS = ("Revenue", "Operating Expenses", "Gross Profit", "Net Income")

# Big-cap set with standard income-statement reporting (excludes banks).
TICKERS = ("AAPL", "MSFT", "META", "AMZN", "NVDA", "GOOGL", "WMT", "TSLA")


def _metrics_with_values(section: dict) -> list[str]:
    return [m["label"] for m in section["metrics"] if m["current"] is not None]


def _missing_labels(section: dict) -> list[str]:
    present = set(_metrics_with_values(section))
    return [label for label in METRIC_LABELS if label not in present]


@pytest.mark.integration
@pytest.mark.parametrize("ticker", TICKERS)
def test_yoy_quarterly_metrics(ticker: str) -> None:
    settings = get_settings()
    with SECClient(settings.sec_user_agent) as client:
        company = resolve(client, ticker)
        assert company is not None, f"Could not resolve {ticker}"

        yoy = compute_yoy(client, company)
        section = yoy["quarterly"]

        assert section["period_end"], f"{ticker} quarterly: no period_end"
        assert section["prior_period_end"], f"{ticker} quarterly: no prior_period_end"

        missing = _missing_labels(section)
        assert not missing, (
            f"{ticker} quarterly missing: {missing} "
            f"(period {section['period_end']} vs {section['prior_period_end']})"
        )


@pytest.mark.integration
@pytest.mark.parametrize("ticker", TICKERS)
def test_yoy_annual_metrics(ticker: str) -> None:
    settings = get_settings()
    with SECClient(settings.sec_user_agent) as client:
        company = resolve(client, ticker)
        assert company is not None, f"Could not resolve {ticker}"

        yoy = compute_yoy(client, company)
        section = yoy["annual"]

        assert section["period_end"], f"{ticker} annual: no period_end"
        assert section["prior_period_end"], f"{ticker} annual: no prior_period_end"

        missing = _missing_labels(section)
        assert not missing, (
            f"{ticker} annual missing: {missing} "
            f"(period {section['period_end']} vs {section['prior_period_end']})"
        )


@pytest.mark.integration
def test_revenue_drives_period_selection(ticker: str = "NVDA") -> None:
    """Regression: NVDA must not fall back to pre-2012 annual periods."""
    settings = get_settings()
    with SECClient(settings.sec_user_agent) as client:
        company = resolve(client, ticker)
        assert company is not None

        yoy = compute_yoy(client, company)
        annual = yoy["annual"]
        assert annual["period_end"] >= "2025-01-01", (
            f"NVDA annual period_end too old: {annual['period_end']}"
        )

        revenue = next(m for m in annual["metrics"] if m["label"] == REVENUE_LABEL)
        assert revenue["current"] is not None
        assert revenue["current"] > 100_000_000_000
