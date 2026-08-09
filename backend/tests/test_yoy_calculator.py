"""Unit tests for YoY period matching (no network)."""

from __future__ import annotations

from app.services.main_extractor import NormalizedFact
from app.services.yoy_calculator import (
    find_prior_period_end,
    pick_period_ends,
    year_ago,
)


def _fact(end: str, *, form: str = "10-Q", start: str | None = "2026-01-01", val: float = 1.0) -> NormalizedFact:
    return NormalizedFact(
        end=end,
        filed="2026-05-01",
        form=form,
        fy=2026,
        fp="Q1",
        val=val,
        start=start,
    )


class TestYearAgo:
    def test_same_month_day(self) -> None:
        assert year_ago("2026-04-26") == "2025-04-26"

    def test_leap_day(self) -> None:
        assert year_ago("2024-02-29") == "2023-02-28"


class TestFindPriorPeriodEnd:
    def test_exact_calendar_match(self) -> None:
        facts = [_fact("2026-06-30"), _fact("2025-06-30")]
        prior = find_prior_period_end(facts, "10-Q", "2026-06-30", prefer="shortest")
        assert prior == "2025-06-30"

    def test_nearby_fiscal_end(self) -> None:
        """NVDA-style off-by-one-day fiscal calendar."""
        facts = [_fact("2026-04-26"), _fact("2025-04-27")]
        prior = find_prior_period_end(facts, "10-Q", "2026-04-26", prefer="shortest")
        assert prior == "2025-04-27"

    def test_rejects_wrong_quarter(self) -> None:
        facts = [_fact("2026-04-26"), _fact("2026-01-25")]
        prior = find_prior_period_end(facts, "10-Q", "2026-04-26", prefer="shortest")
        assert prior is None

    def test_rejects_too_far_from_target(self) -> None:
        facts = [_fact("2026-04-26"), _fact("2025-03-01")]
        prior = find_prior_period_end(facts, "10-Q", "2026-04-26", prefer="shortest")
        assert prior is None


class TestPickPeriodEnds:
    def test_picks_most_recent_pair(self) -> None:
        facts = [
            _fact("2011-07-31", form="10-K", start="2010-08-01"),
            _fact("2010-07-31", form="10-K", start="2009-08-01"),
            _fact("2026-01-25", form="10-K", start="2025-01-26"),
            _fact("2025-01-26", form="10-K", start="2024-01-28"),
        ]
        ends = pick_period_ends(facts, "10-K")
        assert ends == ("2026-01-25", "2025-01-26")

    def test_returns_none_when_no_pair(self) -> None:
        facts = [_fact("2026-04-26")]
        assert pick_period_ends(facts, "10-Q") is None
