"""Report and history routes."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.report import HistoryItem, HistoryResponse, ReportResponse
from app.routes.deps import get_db, get_sec_client
from app.services.ingest import SECClient
from app.services.report_service import (
    get_or_create_report,
    get_report_by_filing_date,
    list_history,
)

router = APIRouter(tags=["reports"])


@router.get("/report", response_model=ReportResponse)
async def get_report(
    ticker: str = Query(..., min_length=1),
    refresh: bool = False,
    filing_date: str | None = None,
    db: Session = Depends(get_db),
    client: SECClient = Depends(get_sec_client),
) -> ReportResponse:
    try:
        if filing_date:
            result = get_report_by_filing_date(db, ticker, filing_date)
            if not result:
                raise HTTPException(status_code=404, detail="Report not found")
            return ReportResponse(**result)

        result = await get_or_create_report(
            client, db, ticker, force_refresh=refresh
        )
        if not result:
            raise HTTPException(status_code=404, detail="Company not found")
        return ReportResponse(**result)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"SEC request failed: {exc}"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/history", response_model=HistoryResponse)
def get_history(
    ticker: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    items = list_history(db, ticker)
    if items is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return HistoryResponse(
        ticker=ticker.upper(),
        items=[HistoryItem(**item) for item in items],
    )
