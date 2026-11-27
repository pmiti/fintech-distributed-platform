"""SQLAlchemy 2.0 async engine and session factory."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Build the engine. No connection is opened until the first query."""
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,  # discard connections dropped by the server
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: expired attributes would trigger implicit (sync)
    # I/O on access, which is not allowed with asyncio.
    return async_sessionmaker(engine, expire_on_commit=False)


async def is_database_available(engine: AsyncEngine, timeout_seconds: float) -> bool:
    async def ping() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(ping(), timeout=timeout_seconds)
    except Exception:  # any failure means "unavailable" for a health probe
        return False
    return True
