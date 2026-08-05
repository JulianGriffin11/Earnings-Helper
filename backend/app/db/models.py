"""ORM models for Company, Report, and Debrief."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    cik: Mapped[str] = mapped_column(String(10), unique=True, index=True)

    reports: Mapped[list["Report"]] = relationship(back_populates="company")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_company_filing_period", "company_id", "filing_date", "period_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    period_type: Mapped[str] = mapped_column(String(16))  # quarterly | annual
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    prior_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    yoy_data: Mapped[dict] = mapped_column(JSONB)
    filing_date: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="reports")
    debrief: Mapped["Debrief | None"] = relationship(back_populates="report")


class Debrief(Base):
    __tablename__ = "debriefs"
    __table_args__ = (UniqueConstraint("report_id", name="uq_debriefs_report_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    debrief_json: Mapped[dict] = mapped_column(JSONB)
    model_used: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    report: Mapped["Report"] = relationship(back_populates="debrief")
