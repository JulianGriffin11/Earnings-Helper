"""Persist and cache YoY reports in Postgres."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Company, Report
from app.services.ingest import SECClient, latest_filing_date
from app.services.resolver import resolve
from app.services.yoy_calculator import compute_yoy

PERIOD_TYPES = ("quarterly", "annual")


def upsert_company(db: Session, company: dict[str, str]) -> Company:
    row = db.query(Company).filter_by(cik=company["cik"]).one_or_none()
    if row is None:
        row = Company(
            ticker=company["ticker"],
            name=company["name"],
            cik=company["cik"],
        )
        db.add(row)
    else:
        row.ticker = company["ticker"]
        row.name = company["name"]
    db.flush()
    return row


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def find_cached_reports(
    db: Session, company_id: int, filing_date: str
) -> dict[str, Report] | None:
    rows = (
        db.query(Report)
        .filter_by(company_id=company_id, filing_date=filing_date)
        .all()
    )
    by_type = {row.period_type: row for row in rows}
    if all(period_type in by_type for period_type in PERIOD_TYPES):
        return by_type
    return None


def assemble_payload(
    company: Company,
    reports: dict[str, Report],
    filing_date: str,
    *,
    cached: bool,
) -> dict[str, Any]:
    return {
        "company": company.name,
        "cik": company.cik,
        "ticker": company.ticker,
        "quarterly": reports["quarterly"].yoy_data,
        "annual": reports["annual"].yoy_data,
        "filing_date": filing_date,
        "cached": cached,
    }


def save_reports(
    db: Session,
    company_id: int,
    filing_date: str,
    yoy: dict[str, Any],
) -> dict[str, Report]:
    saved: dict[str, Report] = {}
    for period_type in PERIOD_TYPES:
        section = yoy[period_type]
        row = Report(
            company_id=company_id,
            period_type=period_type,
            period_end=parse_date(section.get("period_end")),
            prior_period_end=parse_date(section.get("prior_period_end")),
            yoy_data=section,
            filing_date=filing_date,
        )
        db.add(row)
        saved[period_type] = row
    db.commit()
    return saved


async def get_or_create_report(
    client: SECClient,
    db: Session,
    query: str,
    *,
    force_refresh: bool = False,
) -> dict[str, Any] | None:
    """Return YoY report from cache or compute, persist on miss."""
    company = await resolve(client, query)
    if not company:
        return None

    db_company = upsert_company(db, company)
    filing_date = await latest_filing_date(client, company["cik"])
    if filing_date is None:
        filing_date = "unknown"

    if not force_refresh:
        cached = find_cached_reports(db, db_company.id, filing_date)
        if cached:
            return assemble_payload(
                db_company, cached, filing_date, cached=True
            )

    yoy = await compute_yoy(client, company)
    reports = save_reports(db, db_company.id, filing_date, yoy)
    return assemble_payload(db_company, reports, filing_date, cached=False)
