"""Report and history routes."""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.report import HistoryItem, HistoryResponse, ReportResponse
from app.core.settings import get_settings
from app.db.database import get_session_factory
from app.routes.deps import get_db, get_sec_client
from app.services.orchestration import ReportService
from app.services.sec_client import SECClient

router = APIRouter(tags=["reports"])


def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def stream_report_events(
    *,
    ticker: str,
    refresh: bool,
    filing_date: str | None,
) -> Iterator[str]:
    settings = get_settings()
    event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

    def emit(message: str) -> None:
        event_queue.put(("progress", message))

    def run_pipeline() -> None:
        db = get_session_factory()()
        try:
            if filing_date:
                service = ReportService(db)
                result = service.get_report_by_filing_date(
                    ticker, filing_date, on_progress=emit
                )
                if not result:
                    event_queue.put(("failure", "Report not found"))
                    return
            else:
                with SECClient(settings.sec_user_agent) as client:
                    service = ReportService(db, client)
                    result = service.get_or_create_report(
                        ticker, force_refresh=refresh, on_progress=emit
                    )
                if not result:
                    event_queue.put(("failure", "Company not found"))
                    return

            report = ReportResponse(**result).model_dump(mode="json")
            event_queue.put(("complete", report))
        except httpx.HTTPError as exc:
            event_queue.put(("failure", f"SEC request failed: {exc}"))
        except ValueError as exc:
            event_queue.put(("failure", str(exc)))
        except Exception as exc:
            event_queue.put(("failure", str(exc)))
        finally:
            db.close()

    worker = threading.Thread(target=run_pipeline, daemon=True)
    worker.start()

    while True:
        event_type, payload = event_queue.get()
        if event_type == "progress":
            yield sse_event("progress", {"message": payload})
            continue
        if event_type == "complete":
            yield sse_event("complete", {"report": payload})
            worker.join(timeout=0)
            break
        if event_type == "failure":
            yield sse_event("failure", {"detail": payload})
            worker.join(timeout=0)
            break


@router.get("/report", response_model=ReportResponse)
def get_report(
    ticker: str = Query(..., min_length=1),
    refresh: bool = False,
    filing_date: str | None = None,
    db: Session = Depends(get_db),
    client: SECClient = Depends(get_sec_client),
) -> ReportResponse:
    try:
        if filing_date:
            result = ReportService(db).get_report_by_filing_date(ticker, filing_date)
            if not result:
                raise HTTPException(status_code=404, detail="Report not found")
            return ReportResponse(**result)

        result = ReportService(db, client).get_or_create_report(
            ticker, force_refresh=refresh
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


@router.get("/report/stream")
def get_report_stream(
    ticker: str = Query(..., min_length=1),
    refresh: bool = False,
    filing_date: str | None = None,
) -> StreamingResponse:
    return StreamingResponse(
        stream_report_events(
            ticker=ticker,
            refresh=refresh,
            filing_date=filing_date,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=HistoryResponse)
def get_history(
    ticker: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    items = ReportService(db).list_history(ticker)
    if items is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return HistoryResponse(
        ticker=ticker.upper(),
        items=[HistoryItem(**item) for item in items],
    )
