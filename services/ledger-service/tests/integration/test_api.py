"""API integration tests against a real, already migrated PostgreSQL.

Skipped unless TEST_DATABASE_URL is set. They insert rows, so point it to a
disposable database (see notes.txt).
"""

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.infrastructure.config import Settings
from src.infrastructure.logging import JsonFormatter

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    assert DATABASE_URL
    app = create_app(Settings(database_url=DATABASE_URL))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await app.state.engine.dispose()


async def create_account(client: AsyncClient, currency: str = "USD") -> str:
    response = await client.post("/accounts", json={"currency": currency})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def operate(
    client: AsyncClient, account_id: str, operation: str, amount: str, currency: str = "USD"
) -> tuple[int, dict]:
    response = await client.post(
        f"/accounts/{account_id}/{operation}",
        json={"amount": amount, "currency": currency},
    )
    return response.status_code, response.json()


async def balance_of(client: AsyncClient, account_id: str) -> str:
    return (await client.get(f"/accounts/{account_id}")).json()["balance"]


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


async def test_health_reports_unreachable_database() -> None:
    app = create_app(Settings(database_url="postgresql+asyncpg://x:x@127.0.0.1:1/x"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        response = await http.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}


async def test_create_credit_debit_are_persisted(client: AsyncClient) -> None:
    account_id = await create_account(client)
    assert await balance_of(client, account_id) == "0.00"

    assert (await operate(client, account_id, "credit", "100.50"))[0] == 200
    status, body = await operate(client, account_id, "debit", "40.25")

    assert (status, body["balance"]) == (200, "60.25")
    assert await balance_of(client, account_id) == "60.25"


async def test_largest_amount_is_exact_and_overflow_is_rejected(client: AsyncClient) -> None:
    account_id = await create_account(client)
    maximum = "9999999999999999.99"
    assert (await operate(client, account_id, "credit", maximum))[1]["balance"] == maximum

    assert (await operate(client, account_id, "credit", "0.01"))[0] == 422
    assert await balance_of(client, account_id) == maximum


async def test_unknown_account_is_404(client: AsyncClient) -> None:
    missing = str(uuid4())
    assert (await client.get(f"/accounts/{missing}")).status_code == 404
    assert (await operate(client, missing, "debit", "1.00"))[0] == 404


async def test_insufficient_funds_is_409_and_balance_is_kept(client: AsyncClient) -> None:
    account_id = await create_account(client)
    await operate(client, account_id, "credit", "10.00")

    assert (await operate(client, account_id, "debit", "10.01"))[0] == 409
    assert await balance_of(client, account_id) == "10.00"


@pytest.mark.parametrize(
    ("amount", "currency"),
    [
        ("0", "USD"),
        ("-1.00", "USD"),
        ("1.001", "USD"),  # would be silently rounded by NUMERIC(18, 2)
        ("10000000000000000", "USD"),
        ("NaN", "USD"),
        (1.5, "USD"),  # JSON float
        ("1.00", "EUR"),  # currency mismatch
        ("1.00", "usd"),
    ],
)
async def test_invalid_operation_is_422(
    client: AsyncClient, amount: object, currency: str
) -> None:
    account_id = await create_account(client)
    response = await client.post(
        f"/accounts/{account_id}/credit",
        json={"amount": amount, "currency": currency},
    )
    assert response.status_code == 422, response.text
    assert await balance_of(client, account_id) == "0.00"


async def test_raw_nan_literal_is_422(client: AsyncClient) -> None:
    response = await client.post(
        f"/accounts/{uuid4()}/credit",
        content='{"amount": NaN, "currency": "USD"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


async def test_concurrent_debits_never_overdraw(client: AsyncClient) -> None:
    """Without SELECT ... FOR UPDATE, concurrent debits read the same balance."""
    account_id = await create_account(client)
    await operate(client, account_id, "credit", "100.00")

    results = await asyncio.gather(
        *(operate(client, account_id, "debit", "10.00") for _ in range(25))
    )

    statuses = [status for status, _ in results]
    assert statuses.count(200) == 10
    assert statuses.count(409) == 15
    assert await balance_of(client, account_id) == "0.00"


async def test_concurrent_credits_are_not_lost(client: AsyncClient) -> None:
    account_id = await create_account(client)

    await asyncio.gather(*(operate(client, account_id, "credit", "1.00") for _ in range(25)))

    assert await balance_of(client, account_id) == "25.00"


async def test_correlation_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Correlation-ID": "abc-123"})
    assert response.headers["X-Correlation-ID"] == "abc-123"


@pytest.mark.parametrize("headers", [{}, {"X-Correlation-ID": "bad id!" * 40}])
async def test_correlation_id_is_generated(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await client.get(f"/accounts/{uuid4()}", headers=headers)
    assert UUID(response.headers["X-Correlation-ID"])


async def test_request_log_is_json_with_correlation_id(client: AsyncClient) -> None:
    lines: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(self.format(record))

    handler = Capture()
    handler.setFormatter(JsonFormatter("ledger-service"))
    logger = logging.getLogger("src.api.middleware")
    logger.addHandler(handler)
    try:
        await client.get("/health", headers={"X-Correlation-ID": "log-test"})
    finally:
        logger.removeHandler(handler)

    entry = json.loads(lines[-1])
    assert entry["correlation_id"] == "log-test"
    assert (entry["path"], entry["status_code"]) == ("/health", 200)
