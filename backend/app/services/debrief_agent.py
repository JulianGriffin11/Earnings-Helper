"""Generate structured earnings debriefs from YoY data via OpenAI."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.core.settings import Settings, get_settings
from app.models.debrief import EarningsDebrief

SYSTEM_PROMPT = """You are an earnings analyst. Interpret the provided YoY financial data.

Rules:
- Do not invent numbers. Every figure you cite must appear in the input JSON.
- Do not perform calculations. Use only the current, prior, dollar_change, and pct_change values provided.
- Focus on what changed and why it might matter operationally.
- For expense_analysis, cover Operating Expenses and any other expense-related metrics in the input.
- For margin_analysis, discuss gross profit trends using the provided data.
- Write 3-5 key_takeaways and 1-3 items_to_watch."""


def build_user_message(yoy_report: dict[str, Any]) -> str:
    payload = {
        "company": yoy_report.get("company"),
        "ticker": yoy_report.get("ticker"),
        "cik": yoy_report.get("cik"),
        "filing_date": yoy_report.get("filing_date"),
        "quarterly": yoy_report.get("quarterly"),
        "annual": yoy_report.get("annual"),
    }
    return json.dumps(payload, indent=2)


def generate_debrief(
    yoy_report: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> EarningsDebrief:
    """Sync OpenAI call — returns structured debrief from YoY JSON."""
    settings = settings or get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(yoy_report)},
        ],
        response_format=EarningsDebrief,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("OpenAI returned no parsed debrief")
    return parsed
