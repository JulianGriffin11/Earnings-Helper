"""Fallback XBRL extraction from filed 10-Q HTML when SEC JSON lags."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.services.main_extractor import NormalizedFact
from app.services.sec_client import SECClient, get_submissions_url

_IX_FRACTION = re.compile(
    r"<ix:nonFraction\b([^>]*?)>([^<]+)</ix:nonFraction>",
    re.IGNORECASE,
)
_ATTR = re.compile(r'(\w+)="([^"]*)"')


def edgar_archive_url(cik: str, accession: str) -> str:
    cik_int = str(int(cik))
    acc_nodash = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}"


def get_latest_10q(client: SECClient, cik: str) -> dict[str, str] | None:
    """Most recent 10-Q filing metadata from EDGAR submissions."""
    submissions = client.fetch_json(get_submissions_url(cik))
    recent = submissions["filings"]["recent"]
    for index, form in enumerate(recent["form"]):
        if form == "10-Q":
            return {
                "report_date": recent["reportDate"][index],
                "filing_date": recent["filingDate"][index],
                "accession": recent["accessionNumber"][index],
            }
    return None


def quarterly_facts_lag(
    cache: dict[str, list[NormalizedFact]],
    tags: list[str],
    report_date: str,
) -> bool:
    """True when aggregated SEC facts haven't caught up to the latest 10-Q."""
    max_end: str | None = None
    for tag in tags:
        for fact in cache.get(tag, []):
            if fact.form != "10-Q":
                continue
            max_end = fact.end if max_end is None else max(max_end, fact.end)
    return max_end is None or report_date > max_end


def merge_facts(
    existing: list[NormalizedFact],
    supplemental: list[NormalizedFact],
) -> list[NormalizedFact]:
    by_key: dict[tuple[str, str | None, str], NormalizedFact] = {
        (fact.end, fact.start, fact.form): fact for fact in existing
    }
    for fact in supplemental:
        key = (fact.end, fact.start, fact.form)
        current = by_key.get(key)
        if current is None or fact.filed >= current.filed:
            by_key[key] = fact
    return sorted(by_key.values(), key=lambda fact: fact.end)


def parse_ixbrl_contexts(html: str) -> dict[str, tuple[str | None, str]]:
    contexts: dict[str, tuple[str | None, str]] = {}
    for match in re.finditer(
        r'<xbrli:context id="([^"]+)">.*?<xbrli:period>(.*?)</xbrli:period>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        context_id = match.group(1)
        period = match.group(2)
        start_match = re.search(
            r"<xbrli:startDate>([^<]+)</xbrli:startDate>", period, re.IGNORECASE
        )
        end_match = re.search(
            r"<xbrli:endDate>([^<]+)</xbrli:endDate>", period, re.IGNORECASE
        )
        instant_match = re.search(
            r"<xbrli:instant>([^<]+)</xbrli:instant>", period, re.IGNORECASE
        )
        if end_match:
            contexts[context_id] = (
                start_match.group(1) if start_match else None,
                end_match.group(1),
            )
        elif instant_match:
            contexts[context_id] = (None, instant_match.group(1))
    return contexts


def parse_ixbrl_tag(name: str) -> str | None:
    if name.startswith("us-gaap:"):
        return name.split(":", 1)[1]
    return None


def parse_ixbrl_value(raw: str, attrs: dict[str, str]) -> float | None:
    cleaned = raw.replace(",", "").strip()
    if not cleaned or cleaned in {"—", "-", "&#8212;"}:
        return None
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        value = float(cleaned)
    except ValueError:
        return None
    scale = int(attrs.get("scale", "0"))
    return value * (10**scale)


def parse_ixbrl_facts(
    html: str,
    *,
    form: str,
    filed: str,
) -> dict[str, list[NormalizedFact]]:
    """Parse us-gaap ix:nonFraction values from inline XBRL."""
    contexts = parse_ixbrl_contexts(html)
    grouped: dict[str, list[NormalizedFact]] = {}

    for match in _IX_FRACTION.finditer(html):
        attrs = dict(_ATTR.findall(match.group(1)))
        name = attrs.get("name")
        context_ref = attrs.get("contextRef")
        if not name or not context_ref:
            continue

        tag = parse_ixbrl_tag(name)
        period = contexts.get(context_ref)
        if tag is None or period is None:
            continue

        start, end = period
        val = parse_ixbrl_value(match.group(2), attrs)
        if val is None:
            continue
        fact = NormalizedFact(
            end=end,
            filed=filed,
            form=form,
            fy=None,
            fp=None,
            val=val,
            start=start,
        )
        grouped.setdefault(tag, []).append(fact)

    return grouped


def instance_document_name(client: SECClient, archive_url: str) -> str | None:
    summary_url = f"{archive_url}/FilingSummary.xml"
    xml_text = client.fetch_text(summary_url)
    root = ET.fromstring(xml_text)
    for report in root.iter("Report"):
        instance = report.attrib.get("instance")
        if instance:
            return instance
    return None


def extract_latest_10q_facts(
    client: SECClient,
    cik: str,
    latest_10q: dict[str, str],
) -> dict[str, list[NormalizedFact]]:
    archive_url = edgar_archive_url(cik, latest_10q["accession"])
    instance = instance_document_name(client, archive_url)
    if instance is None:
        return {}

    html = client.fetch_text(f"{archive_url}/{instance}")
    return parse_ixbrl_facts(
        html,
        form="10-Q",
        filed=latest_10q["filing_date"],
    )
