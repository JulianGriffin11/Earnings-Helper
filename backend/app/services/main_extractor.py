"""Primary XBRL extraction from SEC companyconcept JSON API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from app.services.sec_client import SECClient, get_company_concept_url

DEFAULT_FORM_TYPES = ("10-Q", "10-K")


@dataclass(frozen=True)
class NormalizedFact:
    end: str
    filed: str
    form: str
    fy: int | None
    fp: str | None
    val: float
    start: str | None = None


def is_duration(fact: dict[str, Any]) -> bool:
    return "start" in fact and "end" in fact


def normalize_observations(
    observations: Iterable[dict[str, Any]],
    form_types: Sequence[str],
) -> list[NormalizedFact]:
    """Prefer duration facts; for each end date keep the latest filed value."""
    allowed = set(form_types)
    best: dict[tuple[str, str | None], tuple[bool, str, NormalizedFact]] = {}

    for obs in observations:
        form = obs.get("form")
        if form not in allowed:
            continue
        if "end" not in obs or "val" not in obs or "filed" not in obs:
            continue

        end = str(obs["end"])
        filed = str(obs["filed"])
        duration = is_duration(obs)
        start = str(obs["start"]) if "start" in obs else None
        candidate = NormalizedFact(
            end=end,
            filed=filed,
            form=str(form),
            fy=obs.get("fy"),
            fp=obs.get("fp"),
            val=float(obs["val"]),
            start=start,
        )

        # Keep each duration variant (QTD vs YTD share the same end date).
        key = (end, start)
        existing = best.get(key)
        if existing is None:
            best[key] = (duration, filed, candidate)
            continue

        existing_is_duration, existing_filed, _ = existing
        # Prefer duration over instant; among equals, keep latest filed.
        if duration and not existing_is_duration:
            best[key] = (duration, filed, candidate)
        elif duration == existing_is_duration and filed > existing_filed:
            best[key] = (duration, filed, candidate)

    return [fact for _, _, fact in sorted(best.values(), key=lambda item: item[2].end)]


def extract_concept(
    client: SECClient,
    cik: str,
    concept: str,
    *,
    taxonomy: str = "us-gaap",
    form_types: Sequence[str] = DEFAULT_FORM_TYPES,
) -> list[NormalizedFact]:
    """Fetch one XBRL concept and return normalized 10-Q / 10-K USD facts."""
    url = get_company_concept_url(cik, concept, taxonomy=taxonomy)
    payload = client.fetch_json(url)
    usd = payload.get("units", {}).get("USD", [])
    return normalize_observations(usd, form_types)
