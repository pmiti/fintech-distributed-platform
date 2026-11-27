"""Immutable value objects."""

import re
from dataclasses import dataclass
from decimal import Decimal

from src.domain.exceptions import CurrencyMismatchError, InvalidAmountError

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class Money:
    """A non-negative monetary amount in a given ISO-4217-style currency.

    Uses Decimal exclusively: floats are rejected to avoid rounding errors.
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise InvalidAmountError("Amount must be a finite Decimal")
        if self.amount < 0:
            raise InvalidAmountError("Amount cannot be negative")
        if not isinstance(self.currency, str) or not _CURRENCY_RE.match(self.currency):
            raise CurrencyMismatchError(f"Invalid currency code: {self.currency!r}")

    @classmethod
    def zero(cls, currency: str) -> "Money":
        return cls(Decimal("0"), currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def _ensure_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"Cannot operate on {self.currency} and {other.currency}"
            )

    def add(self, other: "Money") -> "Money":
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Return self - other; raises InvalidAmountError if the result is negative."""
        self._ensure_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __ge__(self, other: "Money") -> bool:
        self._ensure_same_currency(other)
        return self.amount >= other.amount
