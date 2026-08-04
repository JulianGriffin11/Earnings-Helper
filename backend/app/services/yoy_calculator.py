"""Compute YoY changes for configured income-statement metrics."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.core.load_metrics import load_metrics
from app.services.extractor import NormalizedFact, extract_concept
from app.services.ingest import SECClient

REVENUE_LABEL = "Revenue"
COGS_TAGS = ["CostOfRevenue", "CostOfGoodsAndServicesSold"]


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

    latest = max(form_facts, key=lambda f: f.end)
    prior_end = year_ago(latest.end)
    if not any(f.end == prior_end for f in form_facts):
        return None

    return latest.end, prior_end


def values_at_ends(
    facts: list[NormalizedFact],
    form: str,
    current_end: str,
    prior_end: str,
) -> tuple[float, float] | None:
    form_facts = [f for f in facts if f.form == form]
    current = next((f for f in form_facts if f.end == current_end), None)
    prior = next((f for f in form_facts if f.end == prior_end), None)
    if current is None or prior is None:
        return None
    return current.val, prior.val


async def fetch_tag_facts(
    client: SECClient,
    cik: str,
    tag: str,
    cache: dict[str, list[NormalizedFact]],
) -> list[NormalizedFact]:
    if tag not in cache:
        try:
            cache[tag] = await extract_concept(client, cik, tag)
        except httpx.HTTPError:
            cache[tag] = []
    return cache[tag]


async def load_facts(
    client: SECClient,
    cik: str,
    tags: list[str],
    cache: dict[str, list[NormalizedFact]],
) -> tuple[str | None, list[NormalizedFact]]:
    """Fetch facts using the first XBRL tag that returns data."""
    for tag in tags:
        facts = await fetch_tag_facts(client, cik, tag, cache)
        if facts:
            return tag, facts
    return None, []


async def values_for_tags(
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
        facts = await fetch_tag_facts(client, cik, tag, cache)
        vals = values_at_ends(facts, form, current_end, prior_end)
        if vals:
            return tag, vals
    return None, None


async def metric_row(
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
    tag, vals = await values_for_tags(
        client, cik, tags, form, current_end, prior_end, cache
    )

    if tag and vals:
        return {"label": label, "tag": tag, **yoy(vals[0], vals[1])}

    if metric.get("derive") == "revenue_minus_cogs":
        rev = computed.get(REVENUE_LABEL, {})
        if rev.get("current") is not None and rev.get("prior") is not None:
            _, cogs_vals = await values_for_tags(
                client, cik, COGS_TAGS, form, current_end, prior_end, cache
            )
            if cogs_vals:
                current = rev["current"] - cogs_vals[0]
                prior = rev["prior"] - cogs_vals[1]
                return {"label": label, "tag": "derived", **yoy(current, prior)}

    return empty_row(label)


async def build_section(
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
        row = await metric_row(
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


async def compute_yoy(client: SECClient, company: dict[str, str]) -> dict[str, Any]:
    """YoY for all configured metrics for a resolved company ({ticker, name, cik})."""
    cik = company["cik"]
    metrics = load_metrics()
    cache: dict[str, list[NormalizedFact]] = {}

    revenue = next(m for m in metrics if m["label"] == REVENUE_LABEL)
    revenue_tags = [revenue["primary"], *revenue.get("fallbacks", [])]
    _, revenue_facts = await load_facts(client, cik, revenue_tags, cache)

    quarterly_ends = pick_period_ends(revenue_facts, "10-Q")
    annual_ends = pick_period_ends(revenue_facts, "10-K")

    quarterly = await build_section(
        client, cik, metrics, quarterly_ends, "10-Q", cache
    )
    annual = await build_section(
        client, cik, metrics, annual_ends, "10-K", cache
    )

    return {
        "company": company.get("name"),
        "cik": cik,
        "ticker": company.get("ticker"),
        "quarterly": quarterly,
        "annual": annual,
    }
