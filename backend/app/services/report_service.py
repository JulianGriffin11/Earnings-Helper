"""Persist and cache YoY reports in Postgres."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import Company, Debrief, Report
from app.models.debrief import EarningsDebrief
from app.services.debrief_agent import generate_debrief
from app.services.ingest import SECClient, latest_filing_date
from app.services.resolver import resolve
from app.services.yoy_calculator import compute_yoy

PERIOD_TYPES = ("quarterly", "annual")
# Cached period_end older than this vs filing_date is treated as stale (≈15 months).
MAX_PERIOD_LAG = timedelta(days=456)


def get_company_by_ticker(db: Session, ticker: str) -> Company | None:
    return db.query(Company).filter_by(ticker=ticker.upper()).one_or_none()


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


def is_stale_cache(reports: dict[str, Report], filing_date: str) -> bool:
    """True when cached YoY periods are too old relative to the filing date."""
    if filing_date == "unknown":
        return False

    quarterly = reports["quarterly"]
    if quarterly.period_end is None:
        return False

    filed = date.fromisoformat(filing_date)
    return quarterly.period_end < filed - MAX_PERIOD_LAG


def find_cached_reports(
    db: Session, company_id: int, filing_date: str
) -> dict[str, Report] | None:
    rows = (
        db.query(Report)
        .filter_by(company_id=company_id, filing_date=filing_date)
        .order_by(Report.created_at.desc())
        .all()
    )
    by_type: dict[str, Report] = {}
    for row in rows:
        by_type.setdefault(row.period_type, row)

    if not all(period_type in by_type for period_type in PERIOD_TYPES):
        return None
    if is_stale_cache(by_type, filing_date):
        return None
    return by_type


def delete_reports_for_filing(
    db: Session, company_id: int, filing_date: str
) -> None:
    rows = (
        db.query(Report)
        .filter_by(company_id=company_id, filing_date=filing_date)
        .all()
    )
    if not rows:
        return

    report_ids = [row.id for row in rows]
    db.query(Debrief).filter(Debrief.report_id.in_(report_ids)).delete(
        synchronize_session=False
    )
    db.query(Report).filter(Report.id.in_(report_ids)).delete(
        synchronize_session=False
    )
    db.flush()


def find_debrief(db: Session, report_id: int) -> Debrief | None:
    return db.query(Debrief).filter_by(report_id=report_id).one_or_none()


def save_debrief(
    db: Session,
    report_id: int,
    debrief: EarningsDebrief,
    model: str,
) -> Debrief:
    row = Debrief(
        report_id=report_id,
        debrief_json=debrief.model_dump(),
        model_used=model,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


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


def attach_debrief(
    payload: dict[str, Any],
    debrief: EarningsDebrief | dict[str, Any],
    *,
    debrief_cached: bool,
) -> dict[str, Any]:
    debrief_data = (
        debrief.model_dump() if isinstance(debrief, EarningsDebrief) else debrief
    )
    return {
        **payload,
        "debrief": debrief_data,
        "debrief_cached": debrief_cached,
    }


def ensure_debrief(
    db: Session,
    payload: dict[str, Any],
    reports: dict[str, Report],
    *,
    force_refresh: bool,
) -> dict[str, Any]:
    quarterly_id = reports["quarterly"].id
    if not force_refresh:
        existing = find_debrief(db, quarterly_id)
        if existing:
            return attach_debrief(
                payload, existing.debrief_json, debrief_cached=True
            )

    settings = get_settings()
    debrief = generate_debrief(payload, settings=settings)
    save_debrief(db, quarterly_id, debrief, settings.openai_model)
    return attach_debrief(payload, debrief, debrief_cached=False)


def save_reports(
    db: Session,
    company_id: int,
    filing_date: str,
    yoy: dict[str, Any],
) -> dict[str, Report]:
    delete_reports_for_filing(db, company_id, filing_date)
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
    for row in saved.values():
        db.refresh(row)
    return saved


async def get_or_create_report(
    client: SECClient,
    db: Session,
    query: str,
    *,
    force_refresh: bool = False,
) -> dict[str, Any] | None:
    """Return YoY report + debrief from cache or compute, persist on miss."""
    company = await resolve(client, query)
    if not company:
        return None

    db_company = upsert_company(db, company)
    filing_date = await latest_filing_date(client, company["cik"])
    if filing_date is None:
        filing_date = "unknown"

    reports: dict[str, Report] | None = None
    cached = False

    if not force_refresh:
        reports = find_cached_reports(db, db_company.id, filing_date)
        if reports:
            cached = True

    if reports is None:
        yoy = await compute_yoy(client, company)
        reports = save_reports(db, db_company.id, filing_date, yoy)
        cached = False

    payload = assemble_payload(db_company, reports, filing_date, cached=cached)
    return ensure_debrief(db, payload, reports, force_refresh=force_refresh)


def list_history(db: Session, ticker: str) -> list[dict[str, Any]] | None:
    """Past quarterly report snapshots for a ticker, newest first."""
    company = get_company_by_ticker(db, ticker)
    if not company:
        return None

    rows = (
        db.query(Report)
        .filter_by(company_id=company.id, period_type="quarterly")
        .order_by(Report.created_at.desc())
        .all()
    )
    return [
        {
            "filing_date": row.filing_date,
            "period_end": row.period_end.isoformat() if row.period_end else None,
            "created_at": row.created_at,
            "report_id": row.id,
        }
        for row in rows
    ]


def get_report_by_filing_date(
    db: Session, ticker: str, filing_date: str
) -> dict[str, Any] | None:
    """Load a cached YoY snapshot (+ debrief if present) from Postgres only."""
    company = get_company_by_ticker(db, ticker)
    if not company:
        return None

    reports = find_cached_reports(db, company.id, filing_date)
    if not reports:
        return None

    payload = assemble_payload(company, reports, filing_date, cached=True)
    existing = find_debrief(db, reports["quarterly"].id)
    if existing:
        return attach_debrief(payload, existing.debrief_json, debrief_cached=True)

    return {**payload, "debrief": None, "debrief_cached": False}
