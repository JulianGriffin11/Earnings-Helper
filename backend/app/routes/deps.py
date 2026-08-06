"""Shared FastAPI dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.database import get_db as get_db_session
from app.services.ingest import SECClient


def get_db() -> Session:
    yield from get_db_session()


async def get_sec_client() -> AsyncGenerator[SECClient, None]:
    settings = get_settings()
    client = SECClient(settings.sec_user_agent)
    try:
        yield client
    finally:
        await client.close()
