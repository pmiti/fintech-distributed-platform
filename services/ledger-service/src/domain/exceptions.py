"""Business exceptions raised by the domain layer."""


class DomainError(Exception):
    """Base class for every business-rule violation."""


class InvalidAmountError(DomainError):
    """Amount is not a valid Decimal, is negative, or is not strictly positive when required."""


class CurrencyMismatchError(DomainError):
    """Operation mixes two different currencies."""


class InsufficientFundsError(DomainError):
    """Debit would leave the account with a negative balance."""


class InactiveAccountError(DomainError):
    """Operation attempted on a deactivated account."""


class AccountNotFoundError(DomainError):
    """No account exists for the given identifier."""
