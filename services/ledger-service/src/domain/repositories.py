"""Repository contracts (structural typing, segregated by responsibility)."""

from typing import Protocol

from src.domain.entities import Account


class AccountReader(Protocol):
    async def get_by_id(
        self, account_id: str, for_update: bool = False
    ) -> Account | None:
        """Return the account, or None if it does not exist.

        Pass for_update=True when the account is going to be modified: the
        implementation must then block concurrent writers until the current
        unit of work ends.
        """
        ...


class AccountWriter(Protocol):
    async def save(self, account: Account) -> None: ...


class AccountRepository(AccountReader, AccountWriter, Protocol):
    """Full read/write contract."""
