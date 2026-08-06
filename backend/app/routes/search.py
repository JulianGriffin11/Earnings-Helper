"""Search routes."""

from fastapi import APIRouter, Depends, Query

from app.models.report import SearchResponse, SearchResult
from app.routes.deps import get_sec_client
from app.services.ingest import SECClient
from app.services.resolver import search

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search_companies(
    q: str = Query(default="", min_length=0),
    client: SECClient = Depends(get_sec_client),
) -> SearchResponse:
    results = await search(client, q)
    return SearchResponse(results=[SearchResult(**item) for item in results])
