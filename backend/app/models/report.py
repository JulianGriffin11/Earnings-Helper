"""API response models for reports and search."""

from pydantic import BaseModel

from app.models.debrief import EarningsDebrief


class MetricRow(BaseModel):
    label: str
    tag: str | None = None
    current: float | None = None
    prior: float | None = None
    dollar_change: float | None = None
    pct_change: float | None = None


class YoYSection(BaseModel):
    period_end: str | None
    prior_period_end: str | None
    metrics: list[MetricRow]


class ReportResponse(BaseModel):
    company: str
    cik: str
    ticker: str
    quarterly: YoYSection
    annual: YoYSection
    filing_date: str
    cached: bool
    debrief: EarningsDebrief | None = None
    debrief_cached: bool = False


class SearchResult(BaseModel):
    ticker: str
    name: str
    cik: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
