"""Compute YoY changes for configured income-statement metrics."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import httpx

from app.core.load_metrics import load_metrics
from app.services.fallback_extractor import (
    extract_latest_10q_facts,
    get_latest_10q,
    merge_facts,
    quarterly_facts_lag,
)
from app.services.main_extractor import NormalizedFact, extract_concept
from app.services.sec_client import SECClient

REVENUE_LABEL = "Revenue"
COGS_TAGS = ["CostOfRevenue", "CostOfGoodsAndServicesSold"]
DurationPreference = Literal["shortest", "longest"]


def duration_days(fact: NormalizedFact) -> int | None:
    if not fact.start:
        return None
    start = date.fromisoformat(fact.start)
    end = date.fromisoformat(fact.end)
    return (end - start).days


def duration_preference(form: str) -> DurationPreference:
    return "longest" if form == "10-K" else "shortest"


def fact_at_end(
    facts: list[NormalizedFact],
    form: str,
    end: str,
    *,
    prefer: DurationPreference,
) -> NormalizedFact | None:
    """Pick one fact for a period end (QTD for 10-Q, full year for 10-K)."""
    duration_candidates = [
        f for f in facts if f.form == form and f.end == end and f.start
    ]
    if duration_candidates:
        if prefer == "shortest":
            return min(duration_candidates, key=lambda f: duration_days(f) or 0)
        return max(duration_candidates, key=lambda f: duration_days(f) or 0)

    instant_candidates = [f for f in facts if f.form == form and f.end == end]
    if not instant_candidates:
        return None
    return max(instant_candidates, key=lambda f: f.filed)


def year_ago(end: str) -> str:
    d = date.fromisoformat(end)
    try:
        return d.replace(year=d.year - 1).isoformat()
    except ValueError:
        return d.replace(year=d.year - 1, day=28).isoformat()


def yoy(current: float, prior: float) -> dict[str, float | None]:
    dollar_change = current - prior
    pct = None if prior == 0 else (current / prior - 1.0) * 100.0
    return {
        "current": current,
        "prior": prior,
        "dollar_change": dollar_change,
        "pct_change": pct,
    }


def empty_row(label: str) -> dict[str, Any]:
    return {
        "label": label,
        "tag": None,
        "current": None,
        "prior": None,
        "dollar_change": None,
        "pct_change": None,
    }


def pick_period_ends(
    facts: list[NormalizedFact],
    form: str,
) -> tuple[str, str] | None:
    """Latest filing period and the same period one year ago."""
    form_facts = [f for f in facts if f.form == form]
    if not form_facts:
        return None

    prefer = duration_preference(form)
    for end in sorted({f.end for f in form_facts}, reverse=True):
        if fact_at_end(facts, form, end, prefer=prefer) is None:
            continue
        prior_end = year_ago(end)
        if fact_at_end(facts, form, prior_end, prefer=prefer) is None:
            continue
        return end, prior_end

    return None


def select_best_period_ends(
    facts_lists: list[list[NormalizedFact]],
    form: str,
) -> tuple[str, str] | None:
    """Pick the YoY period pair with the most recent current end across tag fact sets."""
    best: tuple[str, str] | None = None
    for facts in facts_lists:
        ends = pick_period_ends(facts, form)
        if ends and (best is None or ends[0] > best[0]):
            best = ends
    return best


def values_at_ends(
    facts: list[NormalizedFact],
    form: str,
    current_end: str,
    prior_end: str,
) -> tuple[float, float] | None:
    prefer = duration_preference(form)
    current = fact_at_end(facts, form, current_end, prefer=prefer)
    prior = fact_at_end(facts, form, prior_end, prefer=prefer)
    if current is None or prior is None:
        return None
    return current.val, prior.val


def supplement_quarterly_cache(
    client: SECClient,
    cik: str,
    cache: dict[str, list[NormalizedFact]],
    seed_tags: list[str],
) -> None:
    """Merge facts from the latest 10-Q filing when aggregated SEC APIs lag."""
    latest_10q = get_latest_10q(client, cik)
    if latest_10q is None:
        return

    for tag in seed_tags:
        fetch_tag_facts(client, cik, tag, cache)

    if not quarterly_facts_lag(cache, seed_tags, latest_10q["report_date"]):
        return

    filing_facts = extract_latest_10q_facts(client, cik, latest_10q)
    for tag, facts in filing_facts.items():
        cache[tag] = merge_facts(cache.get(tag, []), facts)


def fetch_tag_facts(
    client: SECClient,
    cik: str,
    tag: str,
    cache: dict[str, list[NormalizedFact]],
) -> list[NormalizedFact]:
    if tag not in cache:
        try:
            cache[tag] = extract_concept(client, cik, tag)
        except httpx.HTTPError:
            cache[tag] = []
    return cache[tag]


def pick_best_period_ends(
    client: SECClient,
    cik: str,
    tags: list[str],
    form: str,
    cache: dict[str, list[NormalizedFact]],
) -> tuple[str, str] | None:
    """Try all tags; return the YoY pair with the most recent current period end."""
    facts_lists: list[list[NormalizedFact]] = []
    for tag in tags:
        facts_lists.append(fetch_tag_facts(client, cik, tag, cache))
    return select_best_period_ends(facts_lists, form)


def values_for_tags(
    client: SECClient,
    cik: str,
    tags: list[str],
    form: str,
    current_end: str,
    prior_end: str,
    cache: dict[str, list[NormalizedFact]],
) -> tuple[str | None, tuple[float, float] | None]:
    """Try each tag until both period ends have values."""
    for tag in tags:
        facts = fetch_tag_facts(client, cik, tag, cache)
        vals = values_at_ends(facts, form, current_end, prior_end)
        if vals:
            return tag, vals
    return None, None


def metric_row(
    client: SECClient,
    cik: str,
    metric: dict[str, Any],
    period_ends: tuple[str, str] | None,
    form: str,
    cache: dict[str, list[NormalizedFact]],
    computed: dict[str, dict[str, float | None]],
) -> dict[str, Any]:
    """YoY for one metric at fixed period ends."""
    label = metric["label"]
    if period_ends is None:
        return empty_row(label)

    current_end, prior_end = period_ends
    tags = [metric["primary"], *metric.get("fallbacks", [])]
    tag, vals = values_for_tags(
        client, cik, tags, form, current_end, prior_end, cache
    )

    if tag and vals:
        return {"label": label, "tag": tag, **yoy(vals[0], vals[1])}

    if metric.get("derive") == "revenue_minus_cogs":
        rev = computed.get(REVENUE_LABEL, {})
        if rev.get("current") is not None and rev.get("prior") is not None:
            _, cogs_vals = values_for_tags(
                client, cik, COGS_TAGS, form, current_end, prior_end, cache
            )
            if cogs_vals:
                current = rev["current"] - cogs_vals[0]
                prior = rev["prior"] - cogs_vals[1]
                return {"label": label, "tag": "derived", **yoy(current, prior)}

    return empty_row(label)


def build_section(
    client: SECClient,
    cik: str,
    metrics: list[dict[str, Any]],
    period_ends: tuple[str, str] | None,
    form: str,
    cache: dict[str, list[NormalizedFact]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    computed: dict[str, dict[str, float | None]] = {}

    for metric in metrics:
        row = metric_row(
            client, cik, metric, period_ends, form, cache, computed
        )
        rows.append(row)
        if row["current"] is not None and row["prior"] is not None:
            computed[row["label"]] = {
                "current": row["current"],
                "prior": row["prior"],
            }

    if period_ends is None:
        return {
            "period_end": None,
            "prior_period_end": None,
            "metrics": rows,
        }

    return {
        "period_end": period_ends[0],
        "prior_period_end": period_ends[1],
        "metrics": rows,
    }


def compute_yoy(client: SECClient, company: dict[str, str]) -> dict[str, Any]:
    """YoY for all configured metrics for a resolved company ({ticker, name, cik})."""
    cik = company["cik"]
    metrics = load_metrics()
    cache: dict[str, list[NormalizedFact]] = {}

    revenue = next(m for m in metrics if m["label"] == REVENUE_LABEL)
    revenue_tags = [revenue["primary"], *revenue.get("fallbacks", [])]

    seed_tags = sorted(
        {
            *revenue_tags,
            *[metric["primary"] for metric in metrics],
            *[
                fallback
                for metric in metrics
                for fallback in metric.get("fallbacks", [])
            ],
            *COGS_TAGS,
        }
    )
    supplement_quarterly_cache(client, cik, cache, seed_tags)

    quarterly_ends = pick_best_period_ends(
        client, cik, revenue_tags, "10-Q", cache
    )
    annual_ends = pick_best_period_ends(
        client, cik, revenue_tags, "10-K", cache
    )

    quarterly = build_section(
        client, cik, metrics, quarterly_ends, "10-Q", cache
    )
    annual = build_section(
        client, cik, metrics, annual_ends, "10-K", cache
    )

    return {
        "company": company.get("name"),
        "cik": cik,
        "ticker": company.get("ticker"),
        "quarterly": quarterly,
        "annual": annual,
    }
