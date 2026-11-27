"""Repository contracts (structural typing, segregated by responsibility)."""

from typing import Protocol

from src.domain.entities import Account


class AccountReader(Protocol):
    async def get_by_id(self, account_id: str) -> Account | None: ...


class AccountWriter(Protocol):
    async def save(self, account: Account) -> None: ...


class AccountRepository(AccountReader, AccountWriter, Protocol):
    """Full read/write contract."""
