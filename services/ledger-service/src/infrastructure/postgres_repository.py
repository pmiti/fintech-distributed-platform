"""PostgreSQL implementation of the account repository."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Account
from src.domain.exceptions import InvalidAmountError
from src.domain.value_objects import Money
from src.infrastructure.models import (
    BALANCE_PRECISION,
    BALANCE_SCALE,
    AccountModel,
)

_SMALLEST_UNIT = Decimal(1).scaleb(-BALANCE_SCALE)
_BALANCE_LIMIT = Decimal(1).scaleb(BALANCE_PRECISION - BALANCE_SCALE)  # exclusive


class PostgresAccountRepository:
    """Satisfies AccountRepository.

    It never commits: the caller owns the transaction, so a row lock taken by
    get_by_id(for_update=True) is held until the whole use case finishes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, account_id: str, for_update: bool = False
    ) -> Account | None:
        statement = select(AccountModel).where(AccountModel.id == account_id)
        if for_update:
            # populate_existing: after acquiring the lock, overwrite any stale
            # copy held in the session's identity map with the current row.
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def save(self, account: Account) -> None:
        """Insert or update. To avoid lost updates, load with for_update first."""
        self._ensure_storable(account.balance)
        await self._session.merge(self._to_model(account))
        await self._session.flush()  # surface database errors here

    @staticmethod
    def _ensure_storable(balance: Money) -> None:
        # PostgreSQL would silently round extra decimals, so reject them instead.
        if balance.amount >= _BALANCE_LIMIT:
            raise InvalidAmountError("Balance exceeds the maximum supported value")
        if balance.amount != balance.amount.quantize(_SMALLEST_UNIT):
            raise InvalidAmountError(
                f"Balance cannot have more than {BALANCE_SCALE} decimal places"
            )

    @staticmethod
    def _to_entity(model: AccountModel) -> Account:
        return Account.restore(
            account_id=model.id,
            balance=Money(model.balance, model.currency),
            active=model.is_active,
        )

    @staticmethod
    def _to_model(account: Account) -> AccountModel:
        return AccountModel(
            id=account.id,
            currency=account.currency,
            balance=account.balance.amount,
            is_active=account.is_active,
        )
