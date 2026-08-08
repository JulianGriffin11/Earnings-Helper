"""Orchestrate YoY report pipeline: SEC → compute → Postgres cache → debrief."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import Company, Debrief, Report
from app.models.debrief import EarningsDebrief
from app.services.debrief_agent import generate_debrief
from app.core.logging import ProgressCallback
from app.services.sec_client import SECClient, latest_filing_date
from app.services.ticker_resolver import resolve
from app.services.yoy_calculator import compute_yoy

PERIOD_TYPES = ("quarterly", "annual")
# Cached period_end older than this vs filing_date is treated as stale (≈15 months).
MAX_PERIOD_LAG = timedelta(days=456)


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


class ReportService:
    """One request's report pipeline — owns the DB session and optional SEC client."""

    def __init__(self, db: Session, client: SECClient | None = None) -> None:
        self.db = db
        self.client = client

    def get_or_create_report(
        self,
        query: str,
        *,
        force_refresh: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any] | None:
        """Return YoY report + debrief from cache or compute, persist on miss."""

        def emit(message: str) -> None:
            if on_progress:
                on_progress(message)

        if self.client is None:
            raise ValueError("SEC client required for get_or_create_report")

        emit(f"Looking up {query}...")
        company = resolve(self.client, query)
        if not company:
            return None

        emit(f"Found {company['ticker']} — {company['name']}")
        emit("Saving company record...")
        db_company = self.upsert_company(company)
        emit("Fetching latest filing date...")
        filing_date = latest_filing_date(self.client, company["cik"])
        if filing_date is None:
            filing_date = "unknown"

        reports: dict[str, Report] | None = None
        cached = False

        emit("Checking cached report...")
        if not force_refresh:
            reports = self.find_cached_reports(db_company.id, filing_date)
            if reports:
                cached = True
                emit("Using cached YoY data")

        if reports is None:
            emit("Computing YoY metrics from SEC filings...")
            yoy = compute_yoy(self.client, company, on_progress=on_progress)
            emit("Saving report to database...")
            reports = self.save_reports(db_company.id, filing_date, yoy)
            cached = False

        payload = assemble_payload(db_company, reports, filing_date, cached=cached)
        result = self.ensure_debrief(
            payload, reports, force_refresh=force_refresh, on_progress=on_progress
        )
        emit("Report ready")
        return result

    def list_history(self, ticker: str) -> list[dict[str, Any]] | None:
        """Past quarterly report snapshots for a ticker, newest first."""
        company = self.get_company_by_ticker(ticker)
        if not company:
            return None

        rows = (
            self.db.query(Report)
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
        self,
        ticker: str,
        filing_date: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any] | None:
        """Load a cached YoY snapshot (+ debrief if present) from Postgres only."""

        def emit(message: str) -> None:
            if on_progress:
                on_progress(message)

        emit(f"Loading cached report for {ticker.upper()}...")
        company = self.get_company_by_ticker(ticker)
        if not company:
            return None

        reports = self.find_cached_reports(company.id, filing_date)
        if not reports:
            return None

        emit("Using cached YoY data")
        payload = assemble_payload(company, reports, filing_date, cached=True)
        existing = self.find_debrief(reports["quarterly"].id)
        if existing:
            emit("Using cached debrief")
            result = attach_debrief(payload, existing.debrief_json, debrief_cached=True)
            emit("Report ready")
            return result

        emit("Report ready")
        return {**payload, "debrief": None, "debrief_cached": False}

    def get_company_by_ticker(self, ticker: str) -> Company | None:
        return self.db.query(Company).filter_by(ticker=ticker.upper()).one_or_none()

    def upsert_company(self, company: dict[str, str]) -> Company:
        row = self.db.query(Company).filter_by(cik=company["cik"]).one_or_none()
        if row is None:
            row = Company(
                ticker=company["ticker"],
                name=company["name"],
                cik=company["cik"],
            )
            self.db.add(row)
        else:
            row.ticker = company["ticker"]
            row.name = company["name"]
        self.db.flush()
        return row

    def find_cached_reports(
        self,
        company_id: int,
        filing_date: str,
    ) -> dict[str, Report] | None:
        rows = (
            self.db.query(Report)
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

    def delete_reports_for_filing(self, company_id: int, filing_date: str) -> None:
        rows = (
            self.db.query(Report)
            .filter_by(company_id=company_id, filing_date=filing_date)
            .all()
        )
        if not rows:
            return

        report_ids = [row.id for row in rows]
        self.db.query(Debrief).filter(Debrief.report_id.in_(report_ids)).delete(
            synchronize_session=False
        )
        self.db.query(Report).filter(Report.id.in_(report_ids)).delete(
            synchronize_session=False
        )
        self.db.flush()

    def find_debrief(self, report_id: int) -> Debrief | None:
        return self.db.query(Debrief).filter_by(report_id=report_id).one_or_none()

    def save_debrief(
        self,
        report_id: int,
        debrief: EarningsDebrief,
        model: str,
    ) -> Debrief:
        row = Debrief(
            report_id=report_id,
            debrief_json=debrief.model_dump(),
            model_used=model,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def ensure_debrief(
        self,
        payload: dict[str, Any],
        reports: dict[str, Report],
        *,
        force_refresh: bool,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:

        def emit(message: str) -> None:
            if on_progress:
                on_progress(message)

        quarterly_id = reports["quarterly"].id
        emit("Checking for cached debrief...")
        if not force_refresh:
            existing = self.find_debrief(quarterly_id)
            if existing:
                emit("Using cached debrief")
                return attach_debrief(
                    payload, existing.debrief_json, debrief_cached=True
                )

        emit("Generating earnings debrief...")
        settings = get_settings()
        debrief = generate_debrief(payload, settings=settings)
        self.save_debrief(quarterly_id, debrief, settings.openai_model)
        return attach_debrief(payload, debrief, debrief_cached=False)

    def save_reports(
        self,
        company_id: int,
        filing_date: str,
        yoy: dict[str, Any],
    ) -> dict[str, Report]:
        self.delete_reports_for_filing(company_id, filing_date)
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
            self.db.add(row)
            saved[period_type] = row
        self.db.commit()
        for row in saved.values():
            self.db.refresh(row)
        return saved
