"""Composition root: builds the FastAPI app and wires its dependencies.

Run with: uvicorn --factory src.api.main:create_app
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.errors import register_exception_handlers
from src.api.middleware import CorrelationIdMiddleware
from src.api.routes import create_router
from src.application.use_cases import AccountService
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.database import (
    create_engine,
    create_session_factory,
    is_database_available,
)
from src.infrastructure.logging import configure_logging
from src.infrastructure.postgres_repository import PostgresAccountRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async def provide_session() -> AsyncIterator[AsyncSession]:
        """One transaction per request: commit on success, rollback on error."""
        async with session_factory.begin() as session:
            yield session

    def provide_account_service(
        # scope="function" commits BEFORE the response is sent, so a client
        # never receives a success for a transaction that then fails.
        session: Annotated[AsyncSession, Depends(provide_session, scope="function")],
    ) -> AccountService:
        repository = PostgresAccountRepository(session)
        return AccountService(reader=repository, writer=repository)

    async def check_database() -> bool:
        return await is_database_available(engine, settings.health_check_timeout_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(title=settings.service_name, lifespan=lifespan)
    app.state.engine = engine
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(create_router(provide_account_service, check_database))
    return app
