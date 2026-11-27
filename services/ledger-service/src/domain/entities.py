"""Domain entities."""

from src.domain.exceptions import (
    InactiveAccountError,
    InsufficientFundsError,
    InvalidAmountError,
)
from src.domain.value_objects import Money


class Account:
    """Account aggregate. The balance can only change through credit() / debit()."""

    def __init__(self, account_id: str, currency: str, active: bool = True) -> None:
        self._id = account_id
        self._balance = Money.zero(currency)
        self._active = active

    @property
    def id(self) -> str:
        return self._id

    @property
    def balance(self) -> Money:
        return self._balance

    @property
    def currency(self) -> str:
        return self._balance.currency

    @property
    def is_active(self) -> bool:
        return self._active

    def _validate_operation(self, amount: Money) -> None:
        if not self._active:
            raise InactiveAccountError(f"Account {self._id} is inactive")
        if amount.is_zero():
            raise InvalidAmountError("Amount must be greater than zero")

    def credit(self, amount: Money) -> None:
        self._validate_operation(amount)
        self._balance = self._balance.add(amount)  # raises on currency mismatch

    def debit(self, amount: Money) -> None:
        self._validate_operation(amount)
        if not self._balance >= amount:  # raises on currency mismatch
            raise InsufficientFundsError(
                f"Balance {self._balance.amount} is lower than {amount.amount}"
            )
        self._balance = self._balance.subtract(amount)

    def deactivate(self) -> None:
        self._active = False
