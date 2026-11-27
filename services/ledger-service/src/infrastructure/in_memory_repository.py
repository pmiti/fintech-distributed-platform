"""In-memory repository, useful for tests and local development."""

from src.domain.entities import Account


class InMemoryAccountRepository:
    """Satisfies AccountRepository; substitutable by any other implementation (LSP)."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    async def get_by_id(
        self, account_id: str, for_update: bool = False
    ) -> Account | None:
        # for_update is accepted to honor the contract; there is no locking here.
        return self._accounts.get(account_id)

    async def save(self, account: Account) -> None:
        self._accounts[account.id] = account
