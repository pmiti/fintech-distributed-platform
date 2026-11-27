"""Request and response schemas (transport layer only)."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.entities import Account

CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$", examples=["USD"])]


class CreateAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: CurrencyCode


class AmountOperationRequest(BaseModel):
    """Body for credit and debit. Sign and zero checks belong to the domain."""

    model_config = ConfigDict(extra="forbid")

    # Matches the NUMERIC(18, 2) column, so nothing is rounded or overflows.
    amount: Annotated[Decimal, Field(max_digits=18, decimal_places=2, examples=["10.50"])]
    currency: CurrencyCode

    @field_validator("amount", mode="before")
    @classmethod
    def reject_json_floats(cls, value: object) -> object:
        # A JSON number with decimals is parsed as float before we see it.
        if isinstance(value, float):
            raise ValueError('Send decimal amounts as strings, e.g. "10.50"')
        return value


class AccountResponse(BaseModel):
    id: str
    currency: str
    balance: str  # string, so clients do not parse money as float
    is_active: bool

    @classmethod
    def from_entity(cls, account: Account) -> "AccountResponse":
        return cls(
            id=account.id,
            currency=account.currency,
            balance=f"{account.balance.amount:.2f}",
            is_active=account.is_active,
        )


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["up", "down"]
