"""REST endpoints. Dependency providers are injected by the composition root."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from src.api.schemas import (
    AccountResponse,
    AmountOperationRequest,
    CreateAccountRequest,
    HealthResponse,
)
from src.application.use_cases import AccountService
from src.domain.value_objects import Money


def create_router(
    provide_service: Callable[..., AccountService],
    check_database: Callable[[], Awaitable[bool]],
) -> APIRouter:
    router = APIRouter()
    Service = Annotated[AccountService, Depends(provide_service)]

    @router.post(
        "/accounts",
        response_model=AccountResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_account(
        body: CreateAccountRequest, service: Service
    ) -> AccountResponse:
        account = await service.create_account(body.currency)
        return AccountResponse.from_entity(account)

    @router.get("/accounts/{account_id}", response_model=AccountResponse)
    async def get_account(account_id: str, service: Service) -> AccountResponse:
        return AccountResponse.from_entity(await service.get_account(account_id))

    @router.post("/accounts/{account_id}/credit", response_model=AccountResponse)
    async def credit_account(
        account_id: str, body: AmountOperationRequest, service: Service
    ) -> AccountResponse:
        amount = Money(body.amount, body.currency)
        return AccountResponse.from_entity(
            await service.credit_account(account_id, amount)
        )

    @router.post("/accounts/{account_id}/debit", response_model=AccountResponse)
    async def debit_account(
        account_id: str, body: AmountOperationRequest, service: Service
    ) -> AccountResponse:
        amount = Money(body.amount, body.currency)
        return AccountResponse.from_entity(
            await service.debit_account(account_id, amount)
        )

    @router.get(
        "/health",
        response_model=HealthResponse,
        responses={503: {"model": HealthResponse}},
    )
    async def health(response: Response) -> HealthResponse:
        if await check_database():
            return HealthResponse(status="ok", database="up")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="down")

    return router
