"""Structured LLM earnings debrief schema."""

from typing import Literal

from pydantic import BaseModel


class MetricHighlight(BaseModel):
    metric: str
    trend: Literal["up", "down", "flat"]
    summary: str


class EarningsDebrief(BaseModel):
    headline: str
    overall_assessment: Literal["strong", "mixed", "weak"]
    revenue_analysis: MetricHighlight
    margin_analysis: str
    expense_analysis: list[MetricHighlight]
    key_takeaways: list[str]
    items_to_watch: list[str]
