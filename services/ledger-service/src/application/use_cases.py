"""Application use cases."""

from uuid import uuid4

from src.domain.entities import Account
from src.domain.exceptions import AccountNotFoundError
from src.domain.repositories import AccountReader, AccountWriter
from src.domain.value_objects import Money


class AccountService:
    """Orchestrates account use cases; depends only on repository protocols."""

    def __init__(self, reader: AccountReader, writer: AccountWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def create_account(self, currency: str) -> Account:
        account = Account(account_id=str(uuid4()), currency=currency)
        await self._writer.save(account)
        return account

    async def get_account(self, account_id: str) -> Account:
        return await self._load(account_id)

    async def _load(self, account_id: str, for_update: bool = False) -> Account:
        account = await self._reader.get_by_id(account_id, for_update=for_update)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found")
        return account

    async def credit_account(self, account_id: str, amount: Money) -> Account:
        account = await self._load(account_id, for_update=True)
        account.credit(amount)
        await self._writer.save(account)
        return account

    async def debit_account(self, account_id: str, amount: Money) -> Account:
        account = await self._load(account_id, for_update=True)
        account.debit(amount)
        await self._writer.save(account)
        return account
